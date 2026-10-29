from pathlib import Path
import subprocess as sp
from PIL import Image,ImageDraw,ImageFont

root=Path('outputs/PersonMatte/test-10s')
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',26)
small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',19)
bg=Image.new('RGB',(1920,480),(15,18,22))
d=ImageDraw.Draw(bg)
for x,title,subtitle in [(0,'01 / SOURCE PLATE','Original RGB + source audio'),(640,'02 / ALPHA MATTE','White holds / black removes / gray blends'),(1280,'03 / TEST COMPOSITE','Estimated foreground over checkerboard')]:
    d.text((x+24,20),title,font=font,fill=(235,237,239))
    d.text((x+24,447),subtitle,font=small,fill=(170,179,187))
d.text((24,410),'CETERIS  /  01:39.5 - 01:49.5  /  240 FRAMES  /  24 FPS',font=small,fill=(142,204,183))
bg.save('work/breakdown-frame.png')
cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-loop','1','-i','work/breakdown-frame.png']
for name in ['plate.mp4','alpha_preview.mp4','composite.mp4']:
    cmd += ['-i',str(root/name)]
cmd+=['-filter_complex','[1:v]scale=640:360[a];[2:v]scale=640:360[b];[3:v]scale=640:360[c];[0:v][a]overlay=0:56[t1];[t1][b]overlay=640:56[t2];[t2][c]overlay=1280:56[out]','-map','[out]','-map','1:a:0?','-t','10','-r','24','-c:v','libx264','-crf','17','-preset','fast','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-movflags','+faststart',str(root/'VFX-breakdown.mp4')]
sp.run(cmd,check=True)
