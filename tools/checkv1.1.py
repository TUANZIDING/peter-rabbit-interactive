"""Validate every chapter media reference, hotspot, word form and speech setting."""
import json
import subprocess
import argparse
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/'play/peter-rabbit'

def check_chapter(n):
    data=json.loads((SITE/f'data/ch{n:02d}v1.0.json').read_text())
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
    assert len(data['comic']['bubbles'])=={1:7,2:8,3:8,4:9}[n] and len(data['lesson'])==10 and len(data['vocabulary']['cards'])==5
    assert sum(len(h['answers']) for h in data['homework']['panels'])=={1:5,2:4,3:4,4:5}[n]
    for file in SITE.rglob('*'):
        if file.is_file() and '_' in file.name:errors.append(f'Filename contains underscore: {file.name}')
    if errors:
        print('\n'.join(errors));raise SystemExit(1)
    print(f'PASS: {len(data["assets"])} images ({2*len(data["assets"])} WebP/JPG files), {len(data["audio"])} MP3 files, {len(references)} content audio references; WebP ≤250 KB; MP3 64 kbps mono; no missing resources.')

    for target in data['findIt']['targets']:
        assert target['visible'] and target['hotspots'],target['id']
        for h in target['hotspots']:
            assert 0<=h['x']<100 and 0<=h['y']<100 and 0<h['w']<=100-h['x']+.01 and 0<h['h']<=100-h['y']+.01,(target['id'],h)
    # Yellow words must have a card and a pronounced form.
    import re
    for b in data['comic']['bubbles']+data['theater']['bubbles']:
        for form in re.findall(r'\*([^*]+)\*',' '.join(b['lines'])):
            form=form.lower();root=data['vocabulary']['variants'].get(form,form)
            assert root in [c['id'] for c in data['vocabulary']['cards']],form
            assert f'w-{form}' in data['audio'],form
    print(f"Chapter {n}: hotspot bounds and all highlighted word forms verified.")

    for item in data['audio'].values():
        assert item['voice']==data['voiceConfig'][item['speaker']][0],item['src']
    for font in ['Fredokav1.0.woff2','Fredokav1.0.ttf','字体许可v1.0.txt']:
        assert (SITE/'fonts'/font).is_file(),font

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--chapter',type=int,choices=[1,2,3,4])
    args=parser.parse_args()
    for n in ([args.chapter] if args.chapter else [1,2,3,4]):check_chapter(n)
    datasets=[json.loads((SITE/f'data/ch{n:02d}v1.0.json').read_text()) for n in [1,2,3,4]]
    for role in ['PETER','MUM','NARR','MCG']:
        configs=[d['voiceConfig'][role] for d in datasets if role in d['voiceConfig']]
        assert all(config==configs[0] for config in configs),role
    assert datasets[1]['voiceConfig']['SPARROWS']==['bf_alice',0.9,1.35]
    print('PASS: shared characters retain the supplied voices, speeds and pitch across chapters.')
