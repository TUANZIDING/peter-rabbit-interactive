import{createRequire}from'node:module';
import{mkdir,writeFile,readFile}from'node:fs/promises';
import{resolve,dirname}from'node:path';
import{fileURLToPath}from'node:url';
const require=createRequire(import.meta.url);
const{chromium,webkit,devices}=require(process.env.PETER_PLAYWRIGHT_MODULE||'playwright');
const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const out=process.env.PETER_QA_OUTPUT||resolve(root,'reports');
const base=process.env.PETER_QA_URL||'http://127.0.0.1:8817/play/peter-rabbit';
const chapter=Number(process.env.PETER_QA_CHAPTER||2);
const data=JSON.parse(await readFile(resolve(root,`play/peter-rabbit/data/ch${String(chapter).padStart(2,'0')}v1.0.json`),'utf8'));
const expected=data.homework.panels.flatMap(h=>h.answers);
const tokens=expected.map(word=>Object.entries(data.homework.forms).find(([key,value])=>value===word.toLowerCase())?.[0]||word.toLowerCase());
const readState=()=>JSON.parse(localStorage.getItem('peter-rabbit-progress-v1'))[new URLSearchParams(location.search).get('n')?'chapter'+new URLSearchParams(location.search).get('n'):'chapter1'];
await mkdir(out,{recursive:true});
const results=[];
function check(value,message){if(!value)throw new Error(message);}
async function until(page,fn,message){await page.waitForFunction(fn,chapter,{timeout:50000}).catch(()=>{throw new Error(message);});}
const configurations=[['iPhone13',{...devices['iPhone 13'],viewport:{width:390,height:844}}],['iPad',{...devices['iPad (gen 7)'],viewport:{width:810,height:1080}}],['iPad横屏',{...devices['iPad (gen 7)'],viewport:{width:1080,height:810}}],['desktop',{viewport:{width:1440,height:1000}}]];
for(const[browserName,type]of[['Chromium',chromium],['WebKit',webkit]]){
 const browser=await type.launch();
 for(const[device,options]of configurations){
  if(process.env.PETER_QA_ONLY && process.env.PETER_QA_ONLY!==`${browserName}-${device}`)continue;
  const context=await browser.newContext({...options,reducedMotion:'reduce'});
  // Observe real speech playback. Exclude the silent one-sample audio-unlock buffer.
  await context.addInitScript(()=>{
   window.qaAudio={active:new Set(),maxActive:Number(sessionStorage.getItem('qa-max-audio')||0),micCalls:Number(sessionStorage.getItem('qa-mic-calls')||0)};
   const start=AudioBufferSourceNode.prototype.start,stop=AudioBufferSourceNode.prototype.stop,disconnect=AudioBufferSourceNode.prototype.disconnect;
   AudioBufferSourceNode.prototype.disconnect=function(...args){window.qaAudio.active.delete(this);return disconnect.apply(this,args);};
   AudioBufferSourceNode.prototype.start=function(...args){if(this.buffer?.length<=1)return start.apply(this,args);window.qaAudio.active.add(this);window.qaAudio.maxActive=Math.max(window.qaAudio.maxActive,window.qaAudio.active.size);sessionStorage.setItem('qa-max-audio',String(window.qaAudio.maxActive));this.addEventListener('ended',()=>window.qaAudio.active.delete(this));return start.apply(this,args);};
   AudioBufferSourceNode.prototype.stop=function(...args){window.qaAudio.active.delete(this);return stop.apply(this,args);};
   if(navigator.mediaDevices?.getUserMedia)navigator.mediaDevices.getUserMedia=()=>{window.qaAudio.micCalls++;sessionStorage.setItem('qa-mic-calls',String(window.qaAudio.micCalls));return Promise.reject(new Error('Microphone must never be requested'));};
  });
  const page=await context.newPage(),errors=[],badResponses=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
  page.on('response',r=>{if(r.status()>=400)badResponses.push(`${r.status()} ${r.url()}`);});
  const screenshot=async name=>{await page.locator('.stamp-celebration').waitFor({state:'hidden',timeout:4000});await page.evaluate(()=>document.fonts.ready);await page.screenshot({path:resolve(out,`ch${chapter}-${browserName}-${device}-${name}v1.1.png`),fullPage:true});};
  try{
   await page.goto(`${base}/index.html`);await screenshot('书架');
   if(chapter!==1)await page.evaluate(()=>localStorage.setItem('peter-rabbit-progress-v1',JSON.stringify({version:1,chapter1:{stamps:[1,2,3,4,5],heard:['b01'],found:['robin'],cards:[],quizDone:true,lessonHeard:[],actDone:true,seconds:315,reminded:false}})));
   await page.goto(`${base}/chapter.html?n=${chapter}`);await page.click('#start');await page.waitForSelector('#start-dialog',{state:'hidden'});
   await until(page,n=>JSON.parse(localStorage.getItem('peter-rabbit-progress-v1')||'null')?.['chapter'+n]?.seconds>=2,'Start did not reach the foreground timer');await until(page,()=>window.qaAudio.active.size===0,'Start audio did not finish');
   for(let stage=1;stage<=5;stage++){
    await page.click(`[data-stage="${stage}"]`);await page.evaluate(()=>Promise.all([...document.images].map(i=>i.decode().catch(()=>{}))));
    const layout=await page.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth+1,broken:[...document.querySelectorAll('#stage img')].filter(i=>!i.naturalWidth).length,bubbles:[...document.querySelectorAll('.bubble,.hw-bubble')].filter(el=>{const a=el.getBoundingClientRect(),b=el.parentElement.getBoundingClientRect();return a.left<b.left-1||a.right>b.right+1||a.top<b.top-1||a.bottom>b.bottom+1;}).map(b=>b.dataset.id||'homework')}));
    check(!layout.overflow,`Horizontal overflow in stage ${stage}`);check(!layout.broken,`Broken image in stage ${stage}`);check(!layout.bubbles.length,`Clipped bubbles in stage ${stage}: ${layout.bubbles}`);
    await screenshot(`第${stage}关`);
    if(stage===1){
     await page.click('[data-action="comic-auto"]');await until(page,n=>JSON.parse(localStorage.getItem('peter-rabbit-progress-v1'))['chapter'+n].stamps.includes(1),'Comic did not complete');
     const newWord=data.comic.bubbles.flatMap(b=>b.lines.join(' ').match(/\*([^*]+)\*/g)||[])[0].slice(1,-1).toLowerCase();await page.click(`[data-word="${newWord}"]`);await page.waitForSelector('#word-dialog[open]');await screenshot('单词弹卡');await page.click('[data-close="word-dialog"]');
     if(device==='iPhone13'){for(let i=0;i<6;i++){await page.click('[data-action="panel-prev"]');}for(let i=0;i<6;i++){await screenshot(`漫画第${i+1}格`);if(i<5)await page.click('[data-action="panel-next"]');}await page.click('[data-action="panel-prev"]');check((await page.textContent('#panel-count'))!=='1 / 6','Mobile pager did not move');}
    }
    if(stage===2){
     await page.click('[data-action="zoom"]');check(await page.locator('.scene-viewport.zoomed').count()===1,'Scene zoom failed');await page.click('[data-action="zoom"]');
     await page.locator('#scene').scrollIntoViewIfNeeded();await page.locator('#scene').click({position:{x:50,y:35}});check(!(await page.evaluate(n=>JSON.parse(localStorage.getItem('peter-rabbit-progress-v1'))['chapter'+n].found.length,chapter)),'Wrong scene point accepted');
     for(const target of data.findIt.targets){const h=target.hotspots[0];const box=await page.locator('#scene').boundingBox();await page.locator('#scene').click({position:{x:(h.x+h.w/2)*box.width/100,y:(h.y+h.h/2)*box.height/100}});await page.waitForTimeout(350);}
     await until(page,n=>JSON.parse(localStorage.getItem('peter-rabbit-progress-v1'))['chapter'+n].stamps.includes(2),'Find it did not complete');
    }
    if(stage===3){
     for(const c of data.vocabulary.cards)await page.click(`[data-flip="${c.id}"]`);
     await page.click('[data-action="quiz-start"]');await screenshot('听音选图');
     for(let q=0;q<5;q++){const audio=await page.locator('.quiz-question [data-audio]').getAttribute('data-audio');await page.click(`[data-choice="${audio.slice(2)}"]`);await page.waitForFunction(expected=>document.querySelector('.quiz-count')?.textContent.startsWith(String(expected))||!document.querySelector('.quiz-count'),q+2);}
     await until(page,n=>JSON.parse(localStorage.getItem('peter-rabbit-progress-v1'))['chapter'+n].stamps.includes(3),'Word quiz did not complete');
    }
    if(stage===4){
     await page.click('[data-action="translation"]');check(await page.locator('.lesson-line .zh').first().isHidden(),'Chinese translation did not hide');await page.click('[data-action="translation"]');
     for(const l of data.theater.lines){await page.click(`[data-audio="${l.audio}"]`);await until(page,()=>window.qaAudio.active.size===0,'Theater line did not finish');}
     await page.click('[data-action="lesson-auto"]');await until(page,n=>JSON.parse(localStorage.getItem('peter-rabbit-progress-v1'))['chapter'+n].lessonHeard.length===10,'Lesson audio did not complete');
     await page.click('[data-role="PETER"]');for(let i=0;i<data.lesson.filter(l=>l.speaker==='PETER').length;i++){await page.waitForSelector('[data-action="actor-next"]');check(await page.evaluate(()=>window.qaAudio.active.size===0),'Child line is not silent');await page.click('[data-action="actor-next"]');}
     await until(page,n=>JSON.parse(localStorage.getItem('peter-rabbit-progress-v1'))['chapter'+n].stamps.includes(4),'Act it out did not complete');
     if(device==='desktop'&&browserName==='Chromium'){const roles=await page.locator('[data-role]').evaluateAll(list=>list.map(el=>el.dataset.role).filter(r=>r!=='PETER'));for(const role of roles){await page.click(`[data-role="${role}"]`);for(let i=0;i<data.lesson.filter(l=>l.speaker===role).length;i++){await page.waitForSelector('[data-action="actor-next"]');check(await page.evaluate(()=>window.qaAudio.active.size===0),'Alternate child role is not silent');await page.click('[data-action="actor-next"]');}await page.waitForSelector('#actor-stage .english');}}
    }
    if(stage===5){
     await page.click(`[data-token="${data.homework.wordbox.find(w=>w!==tokens[0])}"]`);await page.click('[data-slot="0"]');await page.click('[data-action="homework-check"]');check(!(await page.evaluate(n=>JSON.parse(localStorage.getItem('peter-rabbit-progress-v1'))['chapter'+n].stamps.includes(5),chapter)),'Wrong homework accepted');
     for(const[i,word]of tokens.entries()){await page.click(`[data-token="${word}"]`);await page.click(`[data-slot="${i}"]`);}
     const filledLayout=await page.evaluate(()=>[...document.querySelectorAll('.hw-blank')].filter(el=>{const a=el.getBoundingClientRect(),b=el.closest('.hw-bubble').getBoundingClientRect();return a.left<b.left-1||a.right>b.right+1||a.width<48||a.height<48;}).length);check(!filledLayout,'Filled slot overflow or touch area below 48px');await screenshot('填词完成');await page.click('[data-action="homework-check"]');await page.waitForSelector('.completion');await screenshot('通关');
    }
   }
   const saved=await page.evaluate(n=>JSON.parse(localStorage.getItem('peter-rabbit-progress-v1'))['chapter'+n],chapter);check(saved.stamps.length===5,'Not all five stamps saved');if(chapter!==1){const legacy=await page.evaluate(()=>JSON.parse(localStorage.getItem('peter-rabbit-progress-v1')).chapter1);check(legacy.stamps.length===5&&legacy.seconds===315,'Legacy chapter1 progress was overwritten');}await page.goto(`${base}/index.html`);check(await page.locator(`[data-chapter-stamps="${chapter}"] .earned`).count()===5,'Shelf does not show chapter stamps');await page.goto(`${base}/chapter.html?n=${chapter}&stage=5`);
   await page.reload();await page.click('#start');check(await page.locator('#reader-stamps .earned').count()===5,'Saved stamps not restored');
   // Restore homework review and exercise actual Pointer Events dragging.
   await page.click('[data-stage="5"]');await page.click('[data-action="homework-replay"]');await page.locator('.wordbox').scrollIntoViewIfNeeded();const from=await page.locator(`[data-token="${tokens[0]}"]`).boundingBox(),to=await page.locator('[data-slot="0"]').boundingBox();await page.mouse.move(from.x+from.width/2,from.y+from.height/2);await page.mouse.down();await page.mouse.move(to.x+to.width/2,to.y+to.height/2,{steps:10});await page.mouse.up();check((await page.textContent('[data-slot="0"]'))===expected[0],'Pointer drag did not fill the slot');
   await page.goto(`${base}/chapter.html?n=${chapter}&debug=1&stage=2`);await page.click('#start');await screenshot('热区核对');check(await page.locator('.hotspot').count()===data.findIt.targets.flatMap(t=>t.hotspots).length,'Debug hotspot count incorrect');
   await context.addInitScript(()=>{if(sessionStorage.getItem('qa-break')){const state=JSON.parse(localStorage.getItem('peter-rabbit-progress-v1'));const key='chapter'+new URLSearchParams(location.search).get('n');state[key].seconds=899;state[key].reminded=false;localStorage.setItem('peter-rabbit-progress-v1',JSON.stringify(state));sessionStorage.removeItem('qa-break');}});await page.evaluate(()=>sessionStorage.setItem('qa-break','yes'));await page.reload();await page.click('#start');await page.waitForSelector('#rest-dialog[open]',{timeout:6000});await page.click('[data-close="rest-dialog"]');
   await page.click('#parent');await page.click('#reset');await page.click('#confirm-reset');check(await page.locator('#reader-stamps .earned').count()===0,'Parent reset failed');await page.click('[data-close="parent-dialog"]');
   const stats=await page.evaluate(()=>({maxActive:window.qaAudio.maxActive,micCalls:window.qaAudio.micCalls}));check(stats.maxActive<=1,'Overlapping audio sources');check(stats.micCalls===0,'Microphone requested');check(!errors.length,`Console/page errors: ${errors}`);check(!badResponses.length,`HTTP errors: ${badResponses}`);
   results.push({chapter,browser:browserName,device,status:'PASS',errors,badResponses,...stats});console.log(`PASS ch${chapter} ${browserName} ${device}: five stages, stamps, quiz, role silence, drag, persistence, reset, break reminder, debug hotspots`);
  }catch(e){const state=await page.evaluate(()=>({feedback:document.querySelector('#feedback')?.textContent,progress:localStorage.getItem('peter-rabbit-progress-v1'),playing:[...document.querySelectorAll('.playing')].map(x=>x.dataset.audio),active:window.qaAudio.active.size,visibility:document.visibilityState}));results.push({chapter,browser:browserName,device,status:'FAIL',message:e.message,state,errors,badResponses});console.log(JSON.stringify(state));console.log(`FAIL ch${chapter} ${browserName} ${device}: ${e.message}`);await screenshot('失败现场');}
  await context.close();
 }
 await browser.close();
}
await writeFile(resolve(out,`第${chapter}章浏览器结果v1.1.json`),JSON.stringify({url:base,flowAudioPlaybackRate:1,results},null,2));
if(results.some(r=>r.status==='FAIL'))process.exitCode=1;
