#!/usr/bin/env python3
"""Normalize 90 source clips and join to a 15-minute H.264 MP4. Requires ffmpeg/ffprobe."""
import argparse,json,subprocess,shutil,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run(args):subprocess.run(args,check=True)
def main():
 p=argparse.ArgumentParser();p.add_argument('--music',type=Path,help='Optional licensed soundtrack file');a=p.parse_args()
 if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):raise SystemExit('Install FFmpeg and FFprobe first')
 shots=json.loads((ROOT/'shots.json').read_text()); missing=[s['id'] for s in shots if not (ROOT/'assets/video'/f"{s['id']}.mp4").exists()]
 if missing:raise SystemExit('Missing source videos: '+', '.join(missing))
 out=ROOT/'output'/'tomkin_lighthouse_15min.mp4';out.parent.mkdir(exist_ok=True)
 with tempfile.TemporaryDirectory(prefix='tomkin_') as td:
  temp=Path(td);normalized=[]
  for s in shots:
   src=ROOT/'assets/video'/f"{s['id']}.mp4";dst=temp/f"{s['id']}.mp4"
   # Normalize every segment to exactly 10 seconds, silence audio if absent; audio is handled by soundtrack separately.
   run(['ffmpeg','-y','-i',str(src),'-an','-vf','fps=24,scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,tpad=stop_mode=clone:stop_duration=10','-t','10','-r','24','-c:v','libx264','-preset','medium','-crf','19','-pix_fmt','yuv420p',str(dst)])
   normalized.append(dst)
  manifest=temp/'concat.txt';manifest.write_text(''.join("file '"+str(f).replace("'", "'\\''")+"'\n" for f in normalized))
  joined=temp/'joined.mp4';run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(manifest),'-c','copy',str(joined)])
  if a.music:
   if not a.music.is_file():raise SystemExit(f'Music not found: {a.music}')
   run(['ffmpeg','-y','-i',str(joined),'-stream_loop','-1','-i',str(a.music),'-map','0:v:0','-map','1:a:0','-t','900','-c:v','copy','-c:a','aac','-b:a','192k','-af','afade=t=out:st=894:d=6','-movflags','+faststart',str(out)])
  else:run(['ffmpeg','-y','-i',str(joined),'-f','lavfi','-i','anullsrc=r=48000:cl=stereo','-map','0:v:0','-map','1:a:0','-t','900','-c:v','copy','-c:a','aac','-shortest','-movflags','+faststart',str(out)])
 print('Created',out)
if __name__=='__main__':main()
