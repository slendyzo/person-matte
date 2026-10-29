from pathlib import Path
import subprocess as sp
import json
import numpy as np
import cv2
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/PersonMatte/depth-showcase'
MATTE = ROOT / 'outputs/PersonMatte/test-10s/person_matte.mov'
AUDIO = ROOT / 'outputs/PersonMatte/test-10s/plate.mp4'
BG = OUT / 'depth-room-neon-v1.png'
W, H, FPS, N = 1920, 1080, 24, 240
FLAGS = 0x08000000

def run(args):
    return sp.run(args, check=True, capture_output=True, creationflags=FLAGS).stdout

# Measure the whole shot, then hold one framing transform to preserve natural motion.
sample = run(['ffmpeg','-v','error','-i',str(MATTE),'-vf',
              'scale=480:270:in_range=tv:out_range=full','-pix_fmt','gray',
              '-f','rawvideo','-'])
small = np.frombuffer(sample,np.uint8).reshape(-1,270,480)
tops, centers = [], []
for frame in small:
    ys,xs = np.where(frame > 128)
    top = int(ys.min())
    head_y, head_x = np.where(frame[top:top+75] > 128)
    tops.append(top*4)
    centers.append(float(np.median(head_x))*4)
scale = (H-175)/(H-float(np.median(tops)))
cx = float(np.median(centers))
transform = np.array([[scale,0,W/2-scale*cx],[0,scale,H*(1-scale)]],np.float32)
background = np.asarray(Image.open(BG).convert('RGB').resize((W,H),Image.Resampling.LANCZOS),dtype=np.float32)/255
dec = sp.Popen(['ffmpeg','-v','error','-i',str(MATTE),'-vf',
                f'scale={W}:{H}:in_range=tv:out_range=full','-pix_fmt','gray16le',
                '-f','rawvideo','-'],stdout=sp.PIPE,creationflags=FLAGS)
silent = ROOT / 'work/neon-centered-silent.mp4'
enc = sp.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24',
                '-s',f'{W}x{H}','-r',str(FPS),'-i','-','-an','-c:v','libx264',
                '-crf','16','-preset','medium','-pix_fmt','yuv420p',str(silent)],
               stdin=sp.PIPE,creationflags=FLAGS)
previews=[]
try:
    for i in range(N):
        data=bytearray()
        while len(data)<W*H*2:
            chunk=dec.stdout.read(W*H*2-len(data))
            if not chunk: raise RuntimeError('Incomplete matte')
            data.extend(chunk)
        a=np.frombuffer(data,'<u2').reshape(H,W).astype(np.float32)/65535
        a=cv2.warpAffine(a,transform,(W,H),flags=cv2.INTER_CUBIC).clip(0,1)[...,None]
        composite=np.round((a+background*(1-a))*255).clip(0,255).astype(np.uint8)
        enc.stdin.write(composite.tobytes())
        if i in (0,120,239):
            preview=OUT/f'neon-centered-{i:03}.jpg'
            Image.fromarray(composite).save(preview,quality=95)
            previews.append(preview)
        if i%48==0: print(f'Rendering {i}/{N}',flush=True)
    dec.stdout.close()
    enc.stdin.close()
    if dec.wait()!=0 or enc.wait()!=0: raise RuntimeError('Video process failed')
finally:
    for p in (dec,enc):
        if p.poll() is None: p.kill()
target=OUT/'CETERIS-neon-room-centered-10s.mp4'
run(['ffmpeg','-v','error','-y','-i',str(silent),'-i',str(AUDIO),'-map','0:v:0',
     '-map','1:a:0','-t','10','-c:v','copy','-c:a','aac','-b:a','192k',
     '-movflags','+faststart',str(target)])
(OUT/'neon-centered-render.json').write_text(json.dumps({
    'size':[W,H],'fps':FPS,'frames':N,'duration':10,'background':BG.name,
    'foreground':'white silhouette, soft alpha edges','scale':scale,
    'source_head_center_x':cx,'transform':transform.tolist(),
    'head_top_range_before': [min(tops),max(tops)],
    'framing':'fixed horizontal head centering; torso extends below frame; median headroom 175px',
    'audio':'original 10-second speech'},indent=2))
print(target,flush=True)
