"""Portable local person matting. Model: github.com/PeterL1n/RobustVideoMatting.
Source for this wrapper is included. See licenses/ for third-party notices.
"""
import argparse
import datetime as dt
from fractions import Fraction
import json
import os
from pathlib import Path
import subprocess as sp
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parent
FFMPEG = str(ROOT / 'bin/ffmpeg.exe')
FFPROBE = str(ROOT / 'bin/ffprobe.exe')
NO_WINDOW = 0x08000000
os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')

def choose_video():
    """Use the Windows picker without depending on Tk or an installed Python."""
    powershell = Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
    script = '''[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new();
Add-Type -AssemblyName System.Windows.Forms;
$picker = New-Object System.Windows.Forms.OpenFileDialog;
$picker.Title = 'Choose video to extract';
$picker.Filter = 'Video files|*.mp4;*.mov;*.mkv;*.avi;*.webm;*.mxf|All files|*.*';
$picker.Multiselect = $true;
if ($picker.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
  ConvertTo-Json -Compress -InputObject @($picker.FileNames)
} else { '[]' }; $picker.Dispose();'''
    result = sp.run([str(powershell), '-NoProfile', '-STA', '-Command', script], capture_output=True, text=True, encoding='utf-8', creationflags=NO_WINDOW, check=True)
    return json.loads(result.stdout.strip().lstrip('\ufeff'))

def probe(source):
    data = sp.check_output([FFPROBE,'-v','error','-show_streams','-show_format','-of','json',str(source)],creationflags=NO_WINDOW)
    info = json.loads(data)
    video = next((s for s in info['streams'] if s['codec_type']=='video' and not s.get('disposition',{}).get('attached_pic')),None)
    if video is None:
        raise ValueError('No video stream was found in this file.')
    return info,video

def frame_rate(video):
    for key in ('avg_frame_rate','r_frame_rate'):
        try:
            rate=Fraction(video.get(key,'0/0'))
            if 0<float(rate)<=240:
                return rate
        except (ValueError,ZeroDivisionError):
            pass
    raise ValueError('The video does not report a usable frame rate.')

def dimensions(video):
    w,h=video['width'],video['height']
    rotation=next((float(s['rotation']) for s in video.get('side_data_list',[]) if 'rotation' in s),float(video.get('tags',{}).get('rotate',0)))
    sar=video.get('sample_aspect_ratio','1:1')
    try:
        sar=Fraction(sar.replace(':','/'))
        if sar<=0: sar=Fraction(1)
    except (ValueError,ZeroDivisionError):
        sar=Fraction(1)
    if abs(round(rotation))%180==90:
        w,h=h,w
        sar=1/sar
    if abs(rotation%90)>0.01:
        raise ValueError('This clip has a non-right-angle rotation. Export an upright copy first.')
    return w,h,sar

def create_session(cpu=False,device_id=None):
    import onnxruntime as ort
    options=ort.SessionOptions()
    options.enable_mem_pattern=False
    options.execution_mode=ort.ExecutionMode.ORT_SEQUENTIAL
    options.intra_op_num_threads=4
    options.log_severity_level=3
    providers=['CPUExecutionProvider']
    if not cpu:
        if 'DmlExecutionProvider' not in ort.get_available_providers():
            raise RuntimeError('The bundled GPU runtime is unavailable. Try EXTRACT - CPU FALLBACK.cmd.')
        config=({'device_id':str(device_id)} if device_id is not None else {'performance_preference':'high_performance','device_filter':'gpu'})
        providers=[('DmlExecutionProvider',config),'CPUExecutionProvider']
    session=ort.InferenceSession(str(ROOT/'models/rvm_mobilenetv3_fp32.onnx'),sess_options=options,providers=providers)
    if not cpu and 'DmlExecutionProvider' not in session.get_providers():
        raise RuntimeError('GPU initialization failed. Update the NVIDIA driver or use the CPU fallback launcher.')
    return session

def read_frame(stream,size):
    frame=bytearray()
    while len(frame)<size:
        chunk=stream.read(size-len(frame))
        if not chunk: break
        frame.extend(chunk)
    if frame and len(frame)!=size:
        raise RuntimeError('The decoder stopped in the middle of a frame.')
    return frame

def extract(source,args,session):
    import numpy as np
    source=Path(source).resolve()
    if not source.is_file(): raise FileNotFoundError(f'Video not found: {source}')
    info,video=probe(source)
    rate=frame_rate(video)
    w,h,sar=dimensions(video)
    fps=f'{rate.numerator}/{rate.denominator}'
    duration_value=video.get('duration',info.get('format',{}).get('duration',0))
    try: available=float(duration_value)-args.start
    except (ValueError,TypeError): available=0
    if available<0: raise ValueError('Start time is beyond the end of the clip.')
    limit=round(args.duration*float(rate)) if args.duration is not None else None
    if limit is not None and limit<1: raise ValueError('The selected duration is shorter than one frame.')
    expected=round(min(available,args.duration or available)*float(rate)) if available>0 else None
    stamp=dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    folder=Path(args.output).resolve() if args.output else source.parent/f'{source.stem}_MATTE_{stamp}'
    folder.mkdir(parents=True,exist_ok=False)
    print(f'\nSource: {source.name}\nOutput: {folder}\nPicture: {w} x {h} | {float(rate):.3f} fps',flush=True)
    print('GPU / DirectML' if not args.cpu else 'CPU fallback / slower',flush=True)
    processes=[]
    start_time=time.perf_counter()
    count=0
    decoder_log=None
    encoder_log=None
    try:
        decoder_log=(folder/'decoder.log').open('wb')
        encoder_log=(folder/'encoder.log').open('wb')
        # Normalize incoming timestamps at the reported average rate. This also
        # handles VFR without dropping the original timing and replaying by index.
        warm_start=max(0,args.start-1)
        warm_frames=round((args.start-warm_start)*float(rate))
        command=[FFMPEG,'-hide_banner','-loglevel','error','-nostdin','-ss',str(warm_start),'-i',str(source),'-map',f'0:{video["index"]}','-vf',f'fps={fps}']
        if limit is not None: command+=['-frames:v',str(limit+warm_frames)]
        command+=['-f','rawvideo','-pix_fmt','rgb24','pipe:1']
        decoder=sp.Popen(command,stdout=sp.PIPE,stderr=decoder_log,creationflags=NO_WINDOW)
        processes.append(decoder)
        filters=f'pad=ceil(iw/2)*2:ceil(ih/2)*2:color=black,scale=in_range=full:out_range=tv,setsar={sar.numerator}/{sar.denominator}'
        command=[FFMPEG,'-hide_banner','-loglevel','error','-nostdin','-y','-f','rawvideo','-pixel_format','gray16le','-video_size',f'{w}x{h}','-framerate',fps,'-i','pipe:0','-an','-vf',filters,'-c:v','prores_ks','-profile:v','3','-pix_fmt','yuv422p10le','-color_range','tv',str(folder/'person_matte.mov')]
        encoder=sp.Popen(command,stdin=sp.PIPE,stderr=encoder_log,creationflags=NO_WINDOW)
        processes.append(encoder)
        rec=[np.zeros((1,1,1,1),dtype=np.float32) for _ in range(4)]
        ratio=np.array([min(512/max(w,h),1)],np.float32)
        frame_index=0
        while True:
            raw=read_frame(decoder.stdout,w*h*3)
            if not raw: break
            rgb=np.frombuffer(raw,np.uint8).reshape(h,w,3)
            src=np.ascontiguousarray(rgb.transpose(2,0,1)[None],dtype=np.float32)/255
            alpha,*rec=session.run(['pha','r1o','r2o','r3o','r4o'],{'src':src,'r1i':rec[0],'r2i':rec[1],'r3i':rec[2],'r4i':rec[3],'downsample_ratio':ratio})
            frame_index+=1
            if frame_index<=warm_frames: continue
            alpha=alpha[0,0].clip(0,1)
            encoder.stdin.write((alpha*65535).round().astype('<u2').tobytes())
            count+=1
            if count%24==0:
                elapsed=time.perf_counter()-start_time
                remaining=max(0,(expected-count)*elapsed/count) if expected else 0
                print(f'{count:,}'+(f' / ~{expected:,}' if expected else '')+f' frames | {count/elapsed:.1f} fps'+(f' | ~{remaining/60:.1f} min left' if expected else ''),flush=True)
        decoder.stdout.close()
        if decoder.wait()!=0: raise RuntimeError('Video decoding failed. See decoder.log in the output folder.')
        encoder.stdin.close()
        if encoder.wait()!=0: raise RuntimeError('Matte encoding failed. See encoder.log in the output folder.')
        if count==0: raise RuntimeError('No frames were produced. Check the source and selected start time.')
        elapsed=time.perf_counter()-start_time
        report={'source':str(source),'start_seconds':args.start,'frames':count,'duration_seconds':count/float(rate),'width':w+w%2,'height':h+h%2,'fps':fps,'sample_aspect_ratio':str(sar),'backend':'CPU' if args.cpu else 'DirectML GPU','elapsed_seconds':round(elapsed,2),'processing_fps':round(count/elapsed,2),'output':'person_matte.mov','format':'10-bit ProRes 422 HQ grayscale/luma matte, no embedded alpha or sound','timing':'Timestamp-normalized CFR at reported average source fps; align by time for variable-frame-rate originals.','model':'RVM MobileNetV3 FP32 ONNX'}
        (folder/'render.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(f'\nDONE - {count:,} frames in {elapsed:.1f} seconds\n{folder / "person_matte.mov"}',flush=True)
        return folder
    except BaseException:
        (folder/'INCOMPLETE.txt').write_text('This export did not finish. Do not use its partial movie. Run again to create a fresh output folder.\n\n'+traceback.format_exc(),encoding='utf-8')
        raise
    finally:
        for process in processes:
            if process.poll() is None: process.kill()
            process.wait()
        for handle in (decoder_log,encoder_log):
            if handle is not None: handle.close()

def main():
    parser=argparse.ArgumentParser(description='Portable local white-on-black person matte extraction.')
    parser.add_argument('sources',nargs='*')
    parser.add_argument('--cpu',action='store_true')
    parser.add_argument('--device-id',type=int)
    parser.add_argument('--start',type=float,default=0)
    parser.add_argument('--duration',type=float)
    parser.add_argument('--output')
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    if args.start<0 or (args.duration is not None and args.duration<=0): parser.error('Start must be >= 0 and duration must be > 0.')
    if args.check:
        session=create_session(args.cpu,args.device_id)
        import numpy as np
        src=np.zeros((1,3,256,256),np.float32)
        feed={'src':src,'downsample_ratio':np.array([1],np.float32)}
        feed.update({f'r{i}i':np.zeros((1,1,1,1),np.float32) for i in range(1,5)})
        result=session.run(['pha'],feed)[0]
        sp.run([FFMPEG,'-v','error','-f','lavfi','-i','color=s=32x32','-frames:v','1','-f','null','-'],check=True,creationflags=NO_WINDOW)
        print('CHECK PASSED: bundled Python, model, inference and FFmpeg work.\nProviders: '+', '.join(session.get_providers()))
        return
    if not args.sources: args.sources=choose_video()
    if not args.sources:
        print('No video selected. Nothing changed.')
        return
    if args.output and len(args.sources)>1: parser.error('--output supports one source only.')
    print('PERSON MATTE - local processing, no uploads\nLoading the model...',flush=True)
    session=create_session(args.cpu,args.device_id)
    for source in args.sources: extract(source,args,session)

if __name__=='__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nCancelled. Any partial export is marked INCOMPLETE.')
        sys.exit(130)
    except Exception as error:
        print(f'\nERROR: {error}\n\nTry the CPU fallback launcher if this is a GPU error. See README.txt for help.',flush=True)
        traceback.print_exc()
        sys.exit(1)
