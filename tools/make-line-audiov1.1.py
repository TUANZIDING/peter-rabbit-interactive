"""Offline British speech; preserve supplied voices and pitch transformation."""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path
import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'play/peter-rabbit'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--chapter', type=int, choices=[1,2,3,4], required=True)
    parser.add_argument('--models', type=Path, default=Path.home()/'peter-prep/models')
    parser.add_argument('--only', nargs='+', help='Regenerate selected audio IDs only')
    parser.add_argument('--samples-only', action='store_true')
    parser.add_argument('--fallback', action='store_true')
    args = parser.parse_args()
    path = SITE / f'data/ch{args.chapter:02d}v1.0.json'
    data = json.loads(path.read_text())
    engine = 'macOS say' if args.fallback else 'kokoro-onnx'
    if not args.fallback:
        from kokoro_onnx import Kokoro
        kokoro = Kokoro(str(args.models/'kokoro-v1.0.onnx'), str(args.models/'voices-v1.0.bin'))
    items = data['audio']
    if args.only: items = {key:items[key] for key in args.only}
    if args.samples_only: items = {k:items[k] for k in ['ui-find-robin','b01','b04','b07']}
    with tempfile.TemporaryDirectory(prefix='peter-audio-') as folder:
        for identifier, item in items.items():
            voice, speed, pitch = data['voiceConfig'][item['speaker']]
            raw = Path(folder)/'speech.wav'
            if args.fallback:
                aiff = Path(folder)/'speech.aiff'
                system_voice = 'Flo (英语（英国）)' if item['speaker'] in ['MUM','GIRLS','SPARROWS','MOUSE'] else 'Daniel'
                subprocess.run(['say','-v',system_voice,'-r','145','-o',str(aiff),item['text']],check=True)
                subprocess.run(['ffmpeg','-y','-v','error','-i',str(aiff),str(raw)],check=True)
            else:
                samples, sr = kokoro.create(item['text'], voice=voice, speed=speed/pitch, lang='en-gb')
                if pitch != 1:
                    samples = np.interp(np.linspace(0,len(samples)-1,int(len(samples)/pitch)),np.arange(len(samples)),samples)
                sf.write(raw, np.asarray(samples,dtype=np.float32), sr)
            # Reverse twice to trim only the end silence; sentence pauses stay intact.
            filters = 'silenceremove=start_periods=1:start_duration=0.02:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_duration=0.02:start_threshold=-45dB,areverse,loudnorm=I=-18:TP=-2:LRA=7'
            destination = Path.home()/f'peter-prep/samples/ch{args.chapter:02d}-{identifier}v1.0.mp3' if args.samples_only else SITE/item['src']
            destination.parent.mkdir(parents=True,exist_ok=True)
            subprocess.run(['ffmpeg','-y','-v','error','-i',str(raw),'-af',filters,'-ar','24000','-ac','1','-c:a','libmp3lame','-b:a','64k',str(destination)],check=True)
            duration = float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(destination)],text=True).strip())
            if not args.samples_only: item.update(duration=duration,engine=engine,voice=voice,bitrate=64000,channels=1)
            print(f'{identifier}: {duration:.2f}s ({engine})',flush=True)
    if not args.samples_only: path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')

if __name__ == '__main__': main()
