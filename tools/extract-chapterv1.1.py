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

def speaker_name(value):
    key = value.upper().replace('MR. ', '').replace(' ', '')
    return {'': 'NARR', 'MCGREGOR': 'MCG'}.get(key, key)

# Hand-labelled after visually inspecting the supplied scenes, in original pixels.
# The exported rectangles/ellipses are percentages; repeated objects are all accepted.
SCENES = {
    2: {
        'robin': [('ellipse',500,390,65,65)],
        'snail': [('ellipse',220,690,86,75)],
        'butterfly': [('ellipse',1125,265,58,67)],
        'shoe': [('ellipse',668,688,92,62)],
        'sparrow': [('ellipse',20,245,100,108),('ellipse',430,235,105,105),('ellipse',800,287,88,86)],
        'barrow': [('rect',285,470,307,158)]},
    3: {
        'mouse': [('ellipse',345,533,73,76)],
        'spider': [('ellipse',328,75,59,64)],
        'gloves': [('rect',184,538,104,107)],
        'hose': [('ellipse',295,228,107,251),('ellipse',28,551,147,201)],
        'rake': [('rect',1080,194,118,121),('rect',1080,305,91,209),('rect',998,683,104,70)],
        'pot': [('rect',548,219,70,62),('rect',621,213,70,67),('rect',815,230,70,54),('rect',776,457,68,61),('rect',978,431,111,112),('rect',0,731,87,108),('rect',1140,617,60,117),('rect',416,353,28,58),('rect',1143,44,57,59)]},
    4: {
        'robin': [('ellipse',490,582,69,60)],
        'frog': [('ellipse',173,852,89,61)],
        'butterfly': [('ellipse',278,773,63,73)],
        'snail': [('ellipse',444,889,51,39)],
        'onion': [('rect',477,683,280,116),('rect',526,849,117,88),('rect',665,848,67,85)],
        'spade': [('rect',480,635,76,236)]}
}
DESCRIPTIONS = {
    2: ['彼得撞见在菜园里的麦格雷戈先生','麦格雷戈先生举耙追赶彼得','彼得跑过菜地，丢掉两只鞋','彼得的外套扣子挂在网上','三只麻雀给被困的彼得鼓劲','彼得挣脱外套，躲过麦格雷戈先生的筛子'],
    3: ['彼得跳进工具棚的喷壶','麦格雷戈先生翻花盆寻找彼得','彼得在喷壶里打喷嚏','彼得从窗户跳出工具棚','彼得向含着豌豆的小老鼠问路','彼得遇见池塘边的白猫'],
    4: ['彼得站在独轮车上看见大门','彼得向大门飞跑','彼得从门底钻出，先生在身后喊','麦格雷戈先生用外套和鞋做成稻草人','累坏的彼得回到家，兔妈妈煮茶','兔妈妈给彼得喂茶，三个姐姐吃晚饭']
}
# Responsive display corrections leave the literal PDF coordinates in sourceRect.
# These positions use open sky/wall/ground, keeping faces visible at 48px touch size.
BUBBLE_RECTS = {
    2: {4: (8,7,39), 5: (2,17,40), 7: (70,76,29)},
    3: {1: (28,5,53), 2: (42,5,52), 3: (58,4,40), 4: (49,5,49), 6: (11,4,45), 8: (11,3,49)},
    4: {1: (11,8,43), 2: (11,8,45), 3: (24,4,39), 4: (71,22,28), 5: (52,5,46), 6: (27,7,44), 7: (43,4,44), 8: (2,21,18), 9: (54,79,44)}
}
HW_RECTS = {
    2: [(51,5,47),(2,4,44),(57,51,41),(3,5,42)],
    3: [(28,3,52),(48,3,50),(2,3,47),(2,3,48)],
    4: [(4,4,47),(4,4,47),(42,0,56),(42,0,56)]
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--kit', required=True, type=Path)
    parser.add_argument('--chapter', type=int, required=True, choices=[2,3,4])
    args = parser.parse_args()
    n = args.chapter
    prefix = f'peter{n:02d}'
    with zipfile.ZipFile(args.kit) as archive:
        def read(name): return archive.read('peter-rabbit-interactive-kit/' + name)
        c = assignment(read(f'content/build_ch{n:02d}.py').decode(), 'C')
        source_audio = read('tools/make_audio.py').decode()
        voices, speakers = assignment(source_audio,'V'), assignment(source_audio,'S')[prefix].split()
        reference = json.loads(read('content/peter_data.json'))[prefix]
        assert len(speakers) == len(c['bubbles'])
        assert [' '.join(b[5]).replace('*','') for b in c['bubbles']] == [b[1] for b in reference['bubbles']]
        assets, audio = {}, {}
        if n==3: voices['CAT']=('bf_lily',0.85,1.1)
        def filename(value):
            stem = Path(value).stem
            if not stem.startswith(prefix): stem = f'{prefix}_{stem}'
            return stem + '_c.jpg'
        def image(identifier, name, alt):
            im = Image.open(io.BytesIO(read('images/' + filename(name)))).convert('RGB')
            original_size = im.size
            im.thumbnail((1200,1200))
            stem = f'ch{n:02d}-{identifier}v1.0'
            webp, jpg = SITE/f'img/{stem}.webp', SITE/f'img/{stem}.jpg'
            webp.parent.mkdir(parents=True,exist_ok=True)
            for quality in [86,80,74,68,60,50]:
                im.save(webp,'WEBP',quality=quality,method=6)
                if webp.stat().st_size <= 250_000: break
            assert webp.stat().st_size <= 250_000
            im.save(jpg,'JPEG',quality=78,optimize=True)
            assets[identifier] = dict(webp=str(webp.relative_to(SITE)),jpg=str(jpg.relative_to(SITE)),width=im.width,height=im.height,alt=alt,originalSize=list(original_size))
            return identifier
        def line(identifier,text,speaker='NARR'):
            who = speaker_name(speaker)
            assert who in voices, who
            audio[identifier] = dict(src=f'audio/ch{n:02d}/{identifier}v1.0.mp3',text=text.replace('*',''),speaker=who,wordTimings=[],timingMode='sentence')
            return identifier
        panels = [dict(id=f'p{i}',image=image(f'panel{i}',f'p{i}',alt)) for i,alt in enumerate(DESCRIPTIONS[n],1)]
        image('spread',c.get('spread_img','spread'),'找物大场景：'+ '、'.join(zh for en,zh in c['findit']))
        basis = [265.1378,197.9696]
        bubbles = []
        for i,(panel,fx,fy,w,h,lines,tail,size) in enumerate(c['bubbles'],1):
            identifier = f'b{i:02d}'
            source_rect = dict(left=fx*100,top=(fy-h/basis[1])*100,width=w/basis[0]*100,height=h/basis[1]*100)
            rect = dict(source_rect)
            if i in BUBBLE_RECTS[n]:
                rect.update(zip(['left','top','width'],BUBBLE_RECTS[n][i]))
            bubbles.append(dict(id=identifier,panel=f'p{panel+1}',lines=lines,text=' '.join(lines).replace('*',''),speaker=speakers[i-1],rect=rect,mobileRect=dict(rect),sourceRect=source_rect,tail=dict(x=tail[0]*100,y=tail[1]*100),fontScale=size/11,audio=line(identifier,' '.join(lines),speakers[i-1]),source=dict(fx=fx,fy=fy,w=w,h=h,size=size)))
        cards = []
        for name,word,ipa,zh,example in c['cards']:
            image(word,name,f'{zh}单词图')
            cards.append(dict(id=word,word=word,ipa=ipa,sourceZh=zh,zh='喷壶（watering can）' if n==3 and word=='can' else zh,example=example,image=word,audio=line(f'w-{word}',word),exampleAudio=line(f'w-{word}-ex',example)))
        variants = {'shoes':'shoe','sparrows':'sparrow'} if n==2 else {}
        variant_ipa = {'shoes':'/ʃuːz/','sparrows':'/ˈspærəʊz/'} if n==2 else {}
        for word in variants: line(f'w-{word}',word)
        scene_w, scene_h = assets['spread']['originalSize']
        crop=dict(x=0,y=290,w=1553,h=668) if n==4 else dict(x=0,y=0,w=scene_w,h=scene_h)
        targets = [dict(id=en,en=en,zh=zh,audio=line(f'ui-find-{en}',f'Find the {en}!' if en!='gloves' else 'Find the gloves!'),hotspots=[dict(shape=shape,x=(x-crop['x'])/crop['w']*100,y=(y-crop['y'])/crop['h']*100,w=w/crop['w']*100,h=h/crop['h']*100) for shape,x,y,w,h in SCENES[n][en]],visible=True) for en,zh in c['findit']]
        lesson = [dict(id=f'l{i:02d}',speaker=speaker_name(who),en=en,zh=zh,audio=line(f'l{i:02d}',en,who)) for i,(who,en,zh) in enumerate(c['lesson'],1)]
        # The unassigned theater is a model dialogue. Ch2 uses the two pictured roles;
        # ch3 cat answer is the supplied narrator voice, since V has no cat voice.
        theater_roles = {2:['MCG','PETER'],3:['PETER','NARR'],4:['MUM','PETER']}[n]
        theater_lines = [dict(en=en,speaker='CAT' if n==3 and i==1 else theater_roles[i%2],audio=line(f't{i+1:02d}',en,('CAT' if n==3 and i==1 else theater_roles[i%2]))) for i,en in enumerate(c['theater']['lines'])]
        theater_bubbles = []
        for i,(x,y,w,h,lines,tail) in enumerate(c['theater']['bubbles']):
            rect = dict(left=x/3,top=(y-h)/2.24,width=w/3,height=h/2.24)
            if n==2 and i==1: rect.update(left=74,top=71,width=24)
            if n==4 and i==0: rect.update(left=31,top=4,width=41)
            if n==4 and i==1: rect.update(left=61,top=40,width=27)
            theater_bubbles.append(dict(id=f'tb{i+1}',lines=lines,rect=rect,sourceTail=dict(x=tail[0]/3,y=tail[1]/2.24),tail=None if n==4 and i==0 else dict(x=tail[0]/3,y=tail[1]/2.24),audio=line(f'tb{i+1}',' '.join(lines),'CAT' if n==3 and i==1 else theater_roles[i%2])))
        theater_name = c['theater']['img']
        if theater_name=='theater': image('theater','theater','彼得在门前跑，旁边的稻草人挂着蓝外套和鞋');theater_image='theater'
        else: theater_image='panel'+re.search(r'p(\d)',theater_name).group(1)
        act = [dict(speaker=speaker_name(who),en=en,audio=line(f'a{i:02d}',en,who)) for i,(who,en) in enumerate(c['act'],1)]
        answer_part = c['answers'].split('|')[0].split(':',1)[1].strip()
        if n==3: answer_words = re.findall(r'\d+\s+([A-Za-z]+)',answer_part)
        else: answer_words = [w.strip() for group in answer_part.split(',') for w in group.split('/')]
        forms = {'shoe':'shoes','sparrow':'sparrows'} if n==2 else {}
        hw,offset = [],0
        for i,(panel,lines,pos,w,tail) in enumerate(c['hw']):
            count = len(re.findall(r'_+',' '.join(lines)))
            answers = answer_words[offset:offset+count];offset += count
            assert len(answers)==count
            left,top,width = HW_RECTS[n][i]
            notes = {2:{0:'shoe → shoes：图里有两只鞋。',2:'sparrow → sparrows：图里有几只麻雀。'},3:{2:'句首用大写 Mouse。'},4:{1:'run 可以用两次；句首变成 Run。'}}
            hw.append(dict(id=f'h{i+1}',panel='p'+re.search(r'p(\d)',panel).group(1),lines=lines,answers=answers,displayAnswers=answers,rect=dict(left=left,top=top,width=width),caption=notes[n].get(i,'点已填的空格，可以换一个词。'),source=dict(fx=pos[0],fy=pos[1],w=w,tail=tail)))
        assert offset==len(answer_words)
        ui = {'ui-start':"Let's read together!",'ui-well-done':'Well done!','ui-try-again':'Try again!','ui-your-turn':'Your turn!','ui-finish':'Well done! Now it is time for your paper homework.','ui-rest':'Great reading! Time for a little break.'}
        for key,text in ui.items(): line(key,text)
        used_voices = {item['speaker'] for item in audio.values()}
        data = dict(schemaVersion='1.1',chapter=dict(number=n,title=c['title'],zhTitle=c['ztitle'],lessonTitle=c['ltitle'],available=True),credits=dict(author='Beatrix Potter',title='The Tale of Peter Rabbit',source='https://www.gutenberg.org/ebooks/14838',illustration='AI-generated; supplied by the project owner'),assets=assets,comic=dict(panels=panels,bubbles=bubbles,sfx=[dict(panel=f'p{p+1}',x=({(2,1):30,(2,4):74,(3,0):70,(3,2):23}.get((n,p),x*100)),y=({(2,1):84,(3,0):84,(3,2):26,(3,3):84,(4,2):84}.get((n,p),y*100)),text=t) for p,x,y,t,*_ in c['sfx']],basis=basis,story=c['story']),findIt=dict(image='spread',targets=targets,coordinateSystem='percent from image top-left',toleranceCssPx=14,omitted=[],crop=crop,decorations=[dict(x=.4,y=3.3,w=22.2,h=11.2,text='LOOK!'),dict(x=69.4,y=89.2,w=30.6,h=8.6,text='FIND 6')] if n==3 else []),vocabulary=dict(cards=cards,extra=[dict(word=w,ipa=ipa,pos=pos,zh=zh) for w,ipa,pos,zh in c['words']],variants=variants,variantIpa=variant_ipa),theater=dict(image=theater_image,intro=c['theater']['intro'],title=theater_lines[0]['en'],bubbles=theater_bubbles,lines=theater_lines,referenceImage='can' if n==3 else None,referenceCaption='Green can · 绿色喷壶' if n==3 else '',practiceNote='家长问，Peter 回答。' if n==4 else ''),lesson=lesson,act=act,actLabel=c['act_label'],actorRoles=['PETER','MCG'] if n in [2,3] else ['PETER','MUM','MCG'],homework=dict(panels=hw,wordbox=c['wordbox'],forms=forms,answersSource=c['answers']),paperHomework=dict(questions=[dict(zh=zh,template=en) for zh,en in c['tr']],prompt='现在去完成纸质作业里的中译英：先说出来，再写下来。'),audio=audio,voiceConfig={key:list(voices[key]) for key in sorted(used_voices)})
        path = SITE/f'data/ch{n:02d}v1.0.json'
        path.parent.mkdir(parents=True,exist_ok=True)
        # Keep expensive generated media metadata on a geometry-only re-extraction.
        if path.exists():
            previous = json.loads(path.read_text())
            for identifier,item in audio.items():
                old = previous.get('audio',{}).get(identifier,{})
                if all(item.get(k)==old.get(k) for k in ['text','speaker','src']):
                    for key in ['duration','engine','voice','bitrate','channels']:
                        if key in old: item[key]=old[key]
        path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
        print(f'Chapter {n}: {len(assets)} images, {len(bubbles)} bubbles, {len(lesson)} lesson lines, {len(audio)} audio references')

if __name__ == '__main__': main()
