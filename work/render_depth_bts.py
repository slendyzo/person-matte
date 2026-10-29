"""Render a continuous 10-second 16:9 plate-to-matte VFX breakdown."""
from pathlib import Path
import json
import subprocess as sp
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W,H,FPS,N=1920,1080,24,240
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/PersonMatte/depth-showcase'
OUT.mkdir(exist_ok=True)
SOURCE=Path(r'F:\TRABALHO\DELPHI DIGITAL\2026-10 CETERIS WEBCAM\riverside_ceteris_raw-video-cfr_hivemind_5385.mp4')
MATTE=ROOT/'outputs/PersonMatte/test-10s/person_matte.mov'
BACKGROUND=OUT/'depth-room.png'
NO_WINDOW=0x08000000

def read_full(stream,size):
    buf=bytearray()
    while len(buf)<size:
        b=stream.read(size-len(buf))
        if not b: break
        buf.extend(b)
    if len(buf)!=size: raise RuntimeError(f'Incomplete frame: {len(buf)}/{size}')
    return buf

def decoder(path,args,pix):
    return sp.Popen(['ffmpeg','-hide_banner','-loglevel','error','-nostdin',*args,'-i',str(path),'-frames:v',str(N),'-vf',f'scale={W}:{H}:in_range={"tv" if pix=="gray16le" else "auto"}:out_range=full','-f','rawvideo','-pix_fmt',pix,'pipe:1'],stdout=sp.PIPE,creationflags=NO_WINDOW)

def encoder(path):
    return sp.Popen(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','pipe:0','-an','-c:v','libx264','-preset','medium','-crf','16','-pix_fmt','yuv420p','-movflags','+faststart',str(path)],stdin=sp.PIPE,creationflags=NO_WINDOW)

def ease(t):
    # Smooth acceleration and deceleration at the ends of every transition.
    t=np.clip(t,0,1)
    return t*t*t*(t*(t*6-15)+10)

def progress(t,a,b): return ease((t-a)/(b-a))

def text_layer(title,subtitle):
    im=Image.new('RGBA',(W,H),(0,0,0,0))
    d=ImageDraw.Draw(im)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',35)
    small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',21)
    mono=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',20)
    d.rounded_rectangle((48,46,407,94),radius=5,fill=(10,10,10,178))
    d.text((65,58),'CETERIS / VFX BREAKDOWN',font=mono,fill=(240,240,240,255))
    d.rounded_rectangle((48,866,650,1018),radius=7,fill=(10,10,10,195))
    d.text((70,886),title,font=font,fill=(245,245,245,255))
    d.text((72,939),subtitle,font=small,fill=(185,185,185,255))
    return np.asarray(im).astype(np.float32)/255

layers=[text_layer('01 / Original plate','Source footage · continuous speech'),
        text_layer('02 / Foreground isolation','Background removed · soft-edge coverage'),
        text_layer('03 / Alpha matte','White holds · black removes · gray blends'),
        text_layer('04 / Depth composite','White silhouette · stylized gray room')]

def overlay(frame,layer,opacity=1):
    a=layer[...,3:4]*opacity
    return frame*(1-a)+layer[...,:3]*a

background=np.asarray(Image.open(BACKGROUND).convert('L').resize((W,H),Image.Resampling.LANCZOS)).astype(np.float32)/255
# Compress the room into supporting gray values; keep the foreground white.
background=np.repeat((0.06+background*.48)[...,None],3,axis=2)
xs=np.arange(W,dtype=np.float32)[None,:,None]
neutral=np.full((H,W,3),.055,dtype=np.float32)
plate=decoder(SOURCE,['-ss','99.5'],'rgb24')
alpha=decoder(MATTE,[],'gray16le')
silent=ROOT/'work/depth-bts-silent.mp4'
clean_silent=ROOT/'work/depth-clean-silent.mp4'
writers=[encoder(silent),encoder(clean_silent)]
snapshots=[]
try:
    for i in range(N):
        t=i/FPS
        rgb=np.frombuffer(read_full(plate.stdout,W*H*3),np.uint8).reshape(H,W,3).astype(np.float32)/255
        a=np.frombuffer(read_full(alpha.stdout,W*H*2),'<u2').reshape(H,W,1).astype(np.float32)/65535
        cutout=rgb*a+neutral*(1-a)
        matte=np.repeat(a,3,axis=2)
        final=matte+background*(1-a)
        if t<3.4:
            reveal=progress(t,1.9,3.4)
            frame=rgb*(1-reveal)+cutout*reveal
        elif t<5.7:
            # A soft traveling wipe reveals the actual alpha rather than a hard key.
            wipe=progress(t,4.05,5.7)*(W+180)-90
            mask=np.clip((wipe-xs+90)/180,0,1)
            mask=mask*mask*(3-2*mask)
            frame=cutout*(1-mask)+matte*mask
        else:
            reveal=progress(t,6.0,7.3)
            frame=matte+background*(1-a)*reveal
        # Label changes dissolve over 12 frames, preserving visual continuity.
        stage_times=[2.55,4.65,6.65]
        idx=sum(t>=v for v in stage_times)
        layer=layers[idx]
        for j,mid in enumerate(stage_times):
            if mid-.25<=t<mid+.25:
                k=progress(t,mid-.25,mid+.25)
                layer=layers[j]*(1-k)+layers[j+1]*k
                break
        frame=overlay(frame,layer)
        out=(frame*255).clip(0,255).astype(np.uint8)
        writers[0].stdin.write(out.tobytes())
        writers[1].stdin.write((final*255).clip(0,255).astype(np.uint8).tobytes())
        if i in (24,84,137,192,239):
            target=OUT/f'stage-{i:03}.jpg'
            Image.fromarray(out).save(target,quality=94)
            snapshots.append(target)
        if (i+1)%48==0: print(f'Rendered {i+1}/{N}',flush=True)
    for p in (plate,alpha):
        p.stdout.close()
        if p.wait()!=0: raise RuntimeError('Decoder failed')
    for p in writers: p.stdin.close()
    for p in writers:
        if p.wait()!=0: raise RuntimeError('Encoder failed')
finally:
    for p in [plate,alpha,*writers]:
        if p.poll() is None: p.kill()

for video,name in [(silent,'CETERIS-VFX-BTS-16x9.mp4'),(clean_silent,'CETERIS-depth-composite-16x9.mp4')]:
    sp.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(video),'-ss','99.5','-i',str(SOURCE),'-map','0:v:0','-map','1:a:0?','-t','10','-c:v','copy','-c:a','aac','-b:a','160k','-movflags','+faststart',str(OUT/name)],check=True,creationflags=NO_WINDOW)
sheet=Image.new('RGB',(960*2,540*2))
for j,p in enumerate(snapshots[:4]):
    sheet.paste(Image.open(p).resize((960,540),Image.Resampling.LANCZOS),((j%2)*960,(j//2)*540))
sheet.save(OUT/'BTS-contact-sheet.jpg',quality=95)
(OUT/'render.json').write_text(json.dumps({'size':[W,H],'fps':FPS,'frames':N,'duration':10,'source_in':99.5,'stages':['original plate','foreground isolation','white alpha matte','silhouette over stylized depth room'],'background':'AI-generated stylized gray depth-pass room, compressed to 6–54% display gray','audio':'continuous original source speech'},indent=2))
print('DONE',OUT,flush=True)
