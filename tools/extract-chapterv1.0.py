"""Extract literal chapter data without importing or executing the source scripts."""
import argparse
import ast
import io
import json
import re
import zipfile
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'play/peter-rabbit'

def literal(node, env):
    if isinstance(node, ast.Constant): return node.value
    if isinstance(node, ast.Name): return env[node.id]
    if isinstance(node, (ast.List, ast.Tuple)):
        values = [literal(x, env) for x in node.elts]
        return tuple(values) if isinstance(node, ast.Tuple) else values
    if isinstance(node, ast.Dict): return {literal(k, env): literal(v, env) for k, v in zip(node.keys, node.values)}
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'dict' and not node.args and all(k.arg for k in node.keywords):
        return {k.arg: literal(k.value, env) for k in node.keywords}
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        value = literal(node.operand, env)
        return -value if isinstance(node.op, ast.USub) else value
    raise ValueError(f'Unsupported data expression: {type(node).__name__}')

def assignment(source, name):
    env = {}
    for node in ast.parse(source).body:
        if not isinstance(node, ast.Assign): continue
        if any(isinstance(t, ast.Name) and t.id == name for t in node.targets): return literal(node.value, env)
        try: value = literal(node.value, env)
        except (KeyError, ValueError): continue
        for target in node.targets:
            if isinstance(target, ast.Name): env[target.id] = value
            elif isinstance(target, ast.Tuple):
                env.update({t.id: v for t, v in zip(target.elts, value) if isinstance(t, ast.Name)})
    raise ValueError(f'Missing {name}')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--kit', required=True, type=Path)
    parser.add_argument('--chapter', type=int, default=1, choices=[1])
    args = parser.parse_args()
    with zipfile.ZipFile(args.kit) as archive:
        def read(name): return archive.read('peter-rabbit-interactive-kit/' + name)
        c = assignment(read('content/build_ch01.py').decode(), 'C')
        source_audio = read('tools/make_audio.py').decode()
        voices, speakers = assignment(source_audio, 'V'), assignment(source_audio, 'S')['peter01'].split()
        reference = json.loads(read('content/peter_data.json'))['peter01']
        assert len(speakers) == len(c['bubbles']) == 7
        assert [' '.join(b[5]).replace('*', '') for b in c['bubbles']] == [b[1] for b in reference['bubbles']]
        assets, audio = {}, {}
        def image(identifier, filename, alt):
            im = Image.open(io.BytesIO(read('images/' + filename))).convert('RGB')
            im.thumbnail((1200, 1200))
            stem = f'ch01-{identifier}v1.0'
            webp, jpg = SITE / f'img/{stem}.webp', SITE / f'img/{stem}.jpg'
            webp.parent.mkdir(parents=True, exist_ok=True)
            for quality in [86, 80, 74, 68, 60, 50]:
                im.save(webp, 'WEBP', quality=quality, method=6)
                if webp.stat().st_size <= 250_000: break
            assert webp.stat().st_size <= 250_000
            im.save(jpg, 'JPEG', quality=78, optimize=True)
            assets[identifier] = dict(webp=str(webp.relative_to(SITE)), jpg=str(jpg.relative_to(SITE)), width=im.width, height=im.height, alt=alt)
            return identifier
        def line(identifier, text, speaker='NARR'):
            speaker = {'': 'NARR', 'Mum': 'MUM', 'Peter': 'PETER'}.get(speaker, speaker)
            assert speaker in voices
            audio[identifier] = dict(src=f'audio/ch01/{identifier}v1.0.mp3', text=text.replace('*', ''), speaker=speaker, wordTimings=[], timingMode='sentence')
            return identifier
        descriptions = ['兔妈妈叮嘱彼得和三个姐姐', '兔妈妈拿着篮子向小兔们告别', '三个姐姐采黑莓，彼得跑向菜园', '彼得从菜园门下钻进去', '彼得吃生菜、豆子和小萝卜', '彼得捂着吃撑的肚子寻找欧芹']
        panels = [dict(id=f'p{i}', image=image(f'panel{i}', f'peter01_p{i}_c.jpg', alt)) for i, alt in enumerate(descriptions, 1)]
        image('spread', 'peter01_spread_c.jpg', '菜园大场景：彼得、白猫、知更鸟、铁锹、小灰鼠、蝴蝶和胡萝卜')
        # PDF page 1 image matrix; fx is left, fy is bottom measured from top.
        basis = [265.1378, 197.9696]
        bubbles = []
        for i, (panel, fx, fy, w, h, lines, tail, size) in enumerate(c['bubbles'], 1):
            identifier = f'b{i:02d}'
            rect = dict(left=fx*100, top=(fy-h/basis[1])*100, width=w/basis[0]*100, height=h/basis[1]*100)
            mobile = dict(rect)
            if i == 1: mobile.update(left=29, top=8, width=43)
            if i == 2: mobile.update(left=73, top=25, width=26)
            bubbles.append(dict(id=identifier, panel=f'p{panel+1}', lines=lines, text=' '.join(lines).replace('*', ''), speaker=speakers[i-1], rect=rect, mobileRect=mobile, tail=dict(x=tail[0]*100, y=tail[1]*100), fontScale=size/11, audio=line(identifier, ' '.join(lines), speakers[i-1]), source=dict(fx=fx, fy=fy, w=w, h=h, size=size)))
        cards = []
        for filename, word, ipa, zh, example in c['cards']:
            image(word, f'peter01_{filename}_c.jpg', f'{zh}单词图')
            cards.append(dict(id=word, word=word, ipa=ipa, zh=zh, example=example, image=word, audio=line(f'w-{word}', word), exampleAudio=line(f'w-{word}-ex', example)))
        for word in ['blackberries', 'radishes']: line(f'w-{word}', word)
        hotspots = {
            'robin': [dict(shape='ellipse', x=20.2, y=42, w=8.8, h=13)],
            'spade': [dict(shape='rect', x=21.5, y=53, w=7.6, h=37)],
            'mouse': [dict(shape='ellipse', x=3.6, y=60.2, w=6.5, h=8.8)],
            'cat': [dict(shape='ellipse', x=24.6, y=11.6, w=10.4, h=9.4)],
            'butterfly': [dict(shape='ellipse', x=90, y=40.5, w=5.4, h=7.2)],
            'carrot': [dict(shape='ellipse', x=x-1.7, y=y-2.4, w=3.4, h=4.8) for x, y in [(78.5,62), (80.9,59.6), (82.8,64), (85.2,61.7), (87.1,65.4), (91.2,65.3), (94.2,61.4), (95.9,68.7)]]
        }
        targets = [dict(id=en, en=en, zh=zh, audio=line(f'ui-find-{en}', f'Find the {en}!'), hotspots=hotspots[en], visible=True) for en, zh in c['findit']]
        lesson = [dict(id=f'l{i:02d}', speaker=who or 'NARR', en=en, zh=zh, audio=line(f'l{i:02d}', en, who)) for i, (who, en, zh) in enumerate(c['lesson'], 1)]
        theater_lines = [dict(en=en, speaker='PETER' if i%2 == 0 else 'MUM', audio=line(f't{i+1:02d}', en, 'PETER' if i%2 == 0 else 'MUM')) for i, en in enumerate(c['theater']['lines'])]
        theater_bubbles = []
        for i, (x, y, w, h, lines, tail) in enumerate(c['theater']['bubbles']):
            theater_bubbles.append(dict(id=f'tb{i+1}', lines=lines, rect=dict(left=x/3, top=(y-h)/2.24, width=w/3, height=h/2.24), sourceTail=dict(x=tail[0]/3, y=tail[1]/2.24), tail=dict(x=95 if i==0 else tail[0]/3, y=61 if i==0 else tail[1]/2.24), audio=line(f'tb{i+1}', ' '.join(lines), 'PETER' if i == 0 else 'MUM')))
        act = [dict(speaker=who.upper(), en=en, audio=line(f'a{i:02d}', en, who)) for i, (who, en) in enumerate(c['act'], 1)]
        expected = [['garden'], ['basket'], ['blackberries'], ['lettuce', 'radishes']]
        hw = []
        for i, (panel, lines, pos, w, tail) in enumerate(c['hw']):
            hw.append(dict(id=f'h{i+1}', panel=panel, lines=lines, answers=expected[i], source=dict(fx=pos[0], fy=pos[1], w=w, tail=tail)))
        ui = {'ui-start': "Let's read together!", 'ui-well-done':'Well done!', 'ui-try-again':'Try again!', 'ui-your-turn':'Your turn!', 'ui-finish':'Well done! Now it is time for your paper homework.', 'ui-rest':'Great reading! Time for a little break.'}
        for key, text in ui.items(): line(key, text)
        data = dict(schemaVersion='1.0', chapter=dict(number=1, title=c['title'], zhTitle=c['ztitle'], lessonTitle=c['ltitle'], available=True), credits=dict(author='Beatrix Potter', title='The Tale of Peter Rabbit', source='https://www.gutenberg.org/ebooks/14838', illustration='AI-generated; supplied by the project owner'), assets=assets, comic=dict(panels=panels, bubbles=bubbles, sfx=[dict(panel=f'p{p+1}', x=x*100, y=y*100, text=t) for p,x,y,t,*_ in c['sfx']], basis=basis, story=c['story']), findIt=dict(image='spread', targets=targets, coordinateSystem='percent from image top-left', toleranceCssPx=14), vocabulary=dict(cards=cards, extra=[dict(word=w, ipa=ipa, pos=pos, zh=zh) for w,ipa,pos,zh in c['words']], variants=dict(blackberries='blackberry', radishes='radish')), theater=dict(image='panel2', intro=c['theater']['intro'], bubbles=theater_bubbles, lines=theater_lines), lesson=lesson, act=act, homework=dict(panels=hw, wordbox=c['wordbox'], forms=dict(blackberry='blackberries', radish='radishes'), answersSource=c['answers']), paperHomework=dict(questions=[dict(zh=zh, template=en) for zh,en in c['tr']], prompt='现在去完成纸质作业里的中译英：先说出来，再写下来。'), audio=audio, voiceConfig={key:list(voices[key]) for key in ['NARR','MUM','GIRLS','PETER']})
        path = SITE / 'data/ch01v1.0.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
        print(f'Extracted: {len(assets)} images, {len(bubbles)} bubbles, {len(lesson)} lesson lines, {len(audio)} audio references')

if __name__ == '__main__': main()
