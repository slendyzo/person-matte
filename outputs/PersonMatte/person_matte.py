"""Local recurrent person matting. RVM model: PeterL1n/RobustVideoMatting."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import shutil
import subprocess as sp
import sys
import time

import numpy as np
import torch
from PIL import Image

ROOT = Path(__file__).resolve().parent
NO_WINDOW = 0x08000000 if os.name == 'nt' else 0

def probe(path):
    return json.loads(sp.check_output(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)], creationflags=NO_WINDOW))

def encoder(path, w, h, fps, master=False):
    command = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-nostdin', '-y', '-f', 'rawvideo', '-pixel_format', 'gray16le' if master else 'rgb24', '-video_size', f'{w}x{h}', '-framerate', fps, '-i', 'pipe:0', '-an']
    if master:
        command += ['-vf', 'scale=in_range=full:out_range=tv', '-c:v', 'prores_ks', '-profile:v', '3', '-pix_fmt', 'yuv422p10le', '-color_range', 'tv']
    else:
        command += ['-c:v', 'libx264', '-preset', 'fast', '-crf', '16', '-pix_fmt', 'yuv420p', '-movflags', '+faststart']
    return sp.Popen(command + [str(path)], stdin=sp.PIPE, creationflags=NO_WINDOW)

def read_frame(stream, size):
    data = bytearray()
    while len(data) < size:
        block = stream.read(size-len(data))
        if not block:
            break
        data.extend(block)
    if data and len(data) != size:
        raise RuntimeError('Decoder returned a partial frame.')
    return data

def extract(source, start=0, duration=None, output=None, review=False):
    source = Path(source).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if start < 0 or (duration is not None and duration <= 0):
        raise ValueError('Start must be nonnegative and duration must be positive.')
    for binary in ('ffmpeg', 'ffprobe'):
        if not shutil.which(binary):
            raise RuntimeError(f'{binary} is not available on PATH.')
    info = probe(source)
    video = next(s for s in info['streams'] if s['codec_type'] == 'video')
    w, h = video['width'], video['height']
    if w % 2 or h % 2:
        raise ValueError('This ProRes preset requires even source width and height.')
    fps = video['avg_frame_rate']
    n, d = map(int, fps.split('/'))
    rate = n/d
    # Audio can outlast the last picture. Never derive a picture count from it.
    video_duration = float(video.get('duration', info['format']['duration']))
    frame_count = str(video.get('nb_frames', ''))
    source_frames = int(frame_count) if frame_count.isdigit() else round(video_duration*rate)
    available = source_frames/rate-start
    if available <= 0:
        raise ValueError('Start is beyond the end of the video.')
    duration = min(duration, available) if duration else available
    total = min(round(duration*rate), max(0,source_frames-round(start*rate)))
    folder = Path(output) if output else source.parent / (source.stem + '_MATTE_' + dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    folder.mkdir(parents=True, exist_ok=False)
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    torch.set_num_threads(4)
    model = torch.jit.load(str(ROOT/'models/rvm_mobilenetv3_fp32.torchscript'), map_location=device).eval()
    model = torch.jit.freeze(model)
    ratio = min(512 / max(w,h), 1.0)
    # One second of preceding frames warms temporal memory before a trimmed test.
    warm_start = max(0, start-1)
    warm_frames = round((start-warm_start)*rate)
    decoder = sp.Popen(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-ss',str(warm_start),'-noautorotate','-i',str(source),'-map','0:v:0','-frames:v',str(total+warm_frames),'-f','rawvideo','-pix_fmt','rgb24','pipe:1'], stdout=sp.PIPE, creationflags=NO_WINDOW)
    writers = []
    started = time.perf_counter()
    count = 0
    try:
        master = encoder(folder/'person_matte.mov', w,h,fps,True)
        writers.append(master)
        if review:
            pw = 960
            ph = round(h*pw/w/2)*2
            previews = [encoder(folder/name,pw,ph,fps) for name in ('plate_silent.mp4','alpha_preview.mp4','composite.mp4')]
            writers.extend(previews)
            yy,xx = np.mgrid[:ph,:pw]
            checker = np.where(((xx//32+yy//32)%2)[...,None],0.23,0.16).astype(np.float32)
            background = np.repeat(checker,3,axis=2)
        rec = [None]*4
        with torch.inference_mode():
            for frame in range(total+warm_frames):
                raw = read_frame(decoder.stdout,w*h*3)
                if not raw:
                    break
                rgb = np.frombuffer(raw,np.uint8).reshape(h,w,3)
                tensor = torch.from_numpy(rgb.copy()).permute(2,0,1).unsqueeze(0).to(device=device,dtype=torch.float32).div_(255)
                foreground,alpha,*rec = model(tensor,*rec,ratio)
                if frame < warm_frames:
                    continue
                a = alpha[0,0].clamp(0,1).cpu().numpy()
                master.stdin.write((a*65535).round().astype('<u2').tobytes())
                if review:
                    src = np.asarray(Image.fromarray(rgb).resize((pw,ph),Image.Resampling.LANCZOS))
                    ap = np.asarray(Image.fromarray(a).resize((pw,ph),Image.Resampling.BILINEAR))[...,None]
                    fg = torch.nn.functional.interpolate(foreground,size=(ph,pw),mode='bilinear',align_corners=False)[0].permute(1,2,0).clamp(0,1).cpu().numpy()
                    comp = ((fg*ap+background*(1-ap))*255).clip(0,255).astype(np.uint8)
                    previews[0].stdin.write(src.tobytes())
                    previews[1].stdin.write(np.repeat((ap*255).round().astype(np.uint8),3,axis=2).tobytes())
                    previews[2].stdin.write(comp.tobytes())
                    if count in (0,total//2,total-1):
                        Image.fromarray(rgb).save(folder/f'plate_{count:04}.png')
                        Image.fromarray((a*65535).round().astype(np.uint16)).save(folder/f'alpha_{count:04}.png')
                        Image.fromarray(comp).save(folder/f'composite_{count:04}.png')
                count += 1
                if count % 24 == 0 or count == total:
                    elapsed=time.perf_counter()-started
                    print(f'{count}/{total} frames | {count/elapsed:.1f} fps | {count/total:.0%}',flush=True)
        decoder.stdout.close()
        if decoder.wait() != 0:
            raise RuntimeError('Video decoding failed.')
        for writer in writers:
            writer.stdin.close()
        for writer in writers:
            if writer.wait() != 0:
                raise RuntimeError('Video encoding failed.')
        if count != total:
            raise RuntimeError(f'Expected {total} frames; received {count}.')
        if review:
            sp.run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y','-i',str(folder/'plate_silent.mp4'),'-ss',str(start),'-t',str(count/rate),'-i',str(source),'-map','0:v:0','-map','1:a:0?','-c:v','copy','-c:a','aac','-b:a','128k','-t',str(count/rate),'-movflags','+faststart',str(folder/'plate.mp4')],check=True,creationflags=NO_WINDOW)
            (folder/'plate_silent.mp4').unlink()
        elapsed=time.perf_counter()-started
        result={'source':str(source),'start_seconds':start,'duration_seconds':count/rate,'frames':count,'width':w,'height':h,'fps':fps,'device':device,'model':'RVM MobileNetV3 fp32','downsample_ratio':ratio,'elapsed_seconds':round(elapsed,2),'processing_fps':round(count/elapsed,2),'matte':'person_matte.mov','encoding':'ProRes 422 HQ, 10-bit luma, video range; neutral chroma','meaning':'white=opaque, black=transparent, gray=partial coverage','source_untouched':True}
        (folder/'render.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(f'DONE: {folder}',flush=True)
        return folder
    except BaseException:
        (folder/'INCOMPLETE.txt').write_text('This export did not complete. Do not use the partial movies. Run the launcher again to create a fresh export.',encoding='utf-8')
        raise
    finally:
        if decoder.poll() is None:
            decoder.kill()
        for writer in writers:
            if writer.poll() is None:
                writer.kill()

def main():
    parser=argparse.ArgumentParser(description='Drop a video onto EXTRACT PERSON.cmd to create a white-on-black ProRes matte.')
    parser.add_argument('sources',nargs='*')
    parser.add_argument('--start',type=float,default=0)
    parser.add_argument('--duration',type=float)
    parser.add_argument('--output')
    parser.add_argument('--review',action='store_true')
    args=parser.parse_args()
    if not args.sources:
        import tkinter as tk
        from tkinter import filedialog
        root=tk.Tk(); root.withdraw()
        args.sources=list(filedialog.askopenfilenames(title='Choose video to extract',filetypes=[('Video','*.mp4 *.mov *.mkv *.avi *.webm'),('All files','*.*')]))
        root.destroy()
    if args.output and len(args.sources)>1:
        parser.error('--output can only be used with one video.')
    for source in args.sources:
        extract(source,args.start,args.duration,args.output,args.review)

if __name__=='__main__':
    main()
