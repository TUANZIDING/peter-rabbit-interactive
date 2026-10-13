"""Validate every published asset and speech reference, including MP3 codec properties."""
import json
import subprocess
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/'play/peter-rabbit'
data=json.loads((SITE/'data/ch01v1.0.json').read_text())
errors=[]
def require(path):
    full=(SITE/path).resolve()
    if not full.is_relative_to(SITE.resolve()): errors.append(f'Path escapes site: {path}')
    elif not full.is_file(): errors.append(f'Missing: {path}')
    return full
for identifier,item in data['assets'].items():
    for kind in ['webp','jpg']:
        file=require(item[kind])
        if file.is_file():
            with Image.open(file) as im:
                if im.width>1200: errors.append(f'Image too wide: {file.name}')
                if (im.width,im.height)!=(item['width'],item['height']):errors.append(f'Dimension mismatch: {file.name}')
            if kind=='webp' and file.stat().st_size>250_000:errors.append(f'WebP too large: {file.name}')
for identifier,item in data['audio'].items():
    file=require(item['src'])
    if not file.is_file():continue
    result=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=codec_name,channels,bit_rate,sample_rate:format=duration','-of','json',str(file)],text=True))
    stream=result['streams'][0]
    if stream.get('codec_name')!='mp3' or stream.get('channels')!=1 or int(stream.get('bit_rate',0))!=64000:errors.append(f'Wrong MP3 settings: {file.name}')
    if float(result['format']['duration'])<=0:errors.append(f'Empty audio: {file.name}')
    if not item.get('duration') or item.get('engine')!='kokoro-onnx':errors.append(f'Missing generation metadata: {identifier}')
references=[]
def walk(value):
    if isinstance(value,dict):
        for key,v in value.items():
            if key in ['audio','exampleAudio'] and isinstance(v,str):references.append(v)
            walk(v)
    elif isinstance(value,list):
        for v in value:walk(v)
walk(data)
for identifier in references:
    if identifier not in data['audio']:errors.append(f'Unknown audio ID: {identifier}')
assert len(data['comic']['bubbles'])==7 and len(data['lesson'])==10 and len(data['vocabulary']['cards'])==5
assert sum(len(h['answers']) for h in data['homework']['panels'])==5
for file in SITE.rglob('*'):
    if file.is_file() and '_' in file.name:errors.append(f'Filename contains underscore: {file.name}')
if errors:
    print('\n'.join(errors));raise SystemExit(1)
print(f'PASS: {len(data["assets"])} images (24 WebP/JPG files), {len(data["audio"])} MP3 files, {len(references)} content audio references; WebP ≤250 KB; MP3 64 kbps mono; no missing resources.')
