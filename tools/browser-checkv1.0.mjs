import{createRequire}from'node:module';
import{mkdir,writeFile,readFile}from'node:fs/promises';
import{resolve,dirname}from'node:path';
import{fileURLToPath}from'node:url';
const require=createRequire(import.meta.url);
const{chromium,webkit,devices}=require(process.env.PETER_PLAYWRIGHT_MODULE||'playwright');
const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const out=process.env.PETER_QA_OUTPUT||resolve(root,'reports');
const base=process.env.PETER_QA_URL||'http://127.0.0.1:8817/play/peter-rabbit';
const data=JSON.parse(await readFile(resolve(root,'play/peter-rabbit/data/ch01v1.0.json'),'utf8'));
await mkdir(out,{recursive:true});
const results=[];
function check(value,message){if(!value)throw new Error(message);}
async function until(page,fn,message){await page.waitForFunction(fn,null,{timeout:40000}).catch(()=>{throw new Error(message);});}
const configurations=[['iPhone13',{...devices['iPhone 13'],viewport:{width:390,height:844}}],['iPad',{...devices['iPad (gen 7)'],viewport:{width:810,height:1080}}],['iPad横屏',{...devices['iPad (gen 7)'],viewport:{width:1080,height:810}}],['desktop',{viewport:{width:1440,height:1000}}]];
for(const[browserName,type]of[['Chromium',chromium],['WebKit',webkit]]){
 const browser=await type.launch();
 for(const[device,options]of configurations){
  if(process.env.PETER_QA_ONLY && process.env.PETER_QA_ONLY!==`${browserName}-${device}`)continue;
  const context=await browser.newContext({...options,reducedMotion:'reduce'});
  // Observe real speech playback. Exclude the silent one-sample audio-unlock buffer.
  await context.addInitScript(()=>{
   window.qaAudio={active:new Set(),maxActive:0,micCalls:0};
   const start=AudioBufferSourceNode.prototype.start,stop=AudioBufferSourceNode.prototype.stop;
   AudioBufferSourceNode.prototype.start=function(...args){if(this.buffer?.length<=1)return start.apply(this,args);window.qaAudio.active.add(this);window.qaAudio.maxActive=Math.max(window.qaAudio.maxActive,window.qaAudio.active.size);this.addEventListener('ended',()=>window.qaAudio.active.delete(this));return start.apply(this,args);};
   AudioBufferSourceNode.prototype.stop=function(...args){window.qaAudio.active.delete(this);return stop.apply(this,args);};
   if(navigator.mediaDevices?.getUserMedia)navigator.mediaDevices.getUserMedia=()=>{window.qaAudio.micCalls++;return Promise.reject(new Error('Microphone must never be requested'));};
  });
  const page=await context.newPage(),errors=[],badResponses=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
  page.on('response',r=>{if(r.status()>=400)badResponses.push(`${r.status()} ${r.url()}`);});
  const screenshot=async name=>{await page.locator('.stamp-celebration').waitFor({state:'hidden',timeout:4000});await page.evaluate(()=>document.fonts.ready);await page.screenshot({path:resolve(out,`${browserName}-${device}-${name}v1.0.png`),fullPage:true});};
  try{
   await page.goto(`${base}/index.html`);await screenshot('书架');
   await page.goto(`${base}/chapter.html?n=1`);await page.click('#start');await page.waitForSelector('#start-dialog',{state:'hidden'});
   await until(page,()=>JSON.parse(localStorage.getItem('peter-rabbit-progress-v1')||'null')?.chapter1.seconds>=2,'Start did not reach the foreground timer');await until(page,()=>window.qaAudio.active.size===0,'Start audio did not finish');
   for(let stage=1;stage<=5;stage++){
    await page.click(`[data-stage="${stage}"]`);await page.evaluate(()=>Promise.all([...document.images].map(i=>i.decode().catch(()=>{}))));
    const layout=await page.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth+1,broken:[...document.querySelectorAll('#stage img')].filter(i=>!i.naturalWidth).length,bubbles:[...document.querySelectorAll('.bubble,.hw-bubble')].filter(el=>{const a=el.getBoundingClientRect(),b=el.parentElement.getBoundingClientRect();return a.left<b.left-1||a.right>b.right+1||a.top<b.top-1||a.bottom>b.bottom+1;}).map(b=>b.dataset.id||'homework')}));
    check(!layout.overflow,`Horizontal overflow in stage ${stage}`);check(!layout.broken,`Broken image in stage ${stage}`);check(!layout.bubbles.length,`Clipped bubbles in stage ${stage}: ${layout.bubbles}`);
    await screenshot(`第${stage}关`);
    if(stage===1){
     await page.click('[data-action="comic-auto"]');await until(page,()=>JSON.parse(localStorage.getItem('peter-rabbit-progress-v1')).chapter1.stamps.includes(1),'Comic did not complete');
     await page.click('[data-word="garden"]');await page.waitForSelector('#word-dialog[open]');await screenshot('单词弹卡');await page.click('[data-close="word-dialog"]');
     if(device==='iPhone13'){await page.click('[data-action="panel-next"]');check((await page.textContent('#panel-count'))!=='1 / 6','Mobile pager did not move');}
    }
    if(stage===2){
     await page.click('[data-action="zoom"]');check(await page.locator('.scene-viewport.zoomed').count()===1,'Scene zoom failed');await page.click('[data-action="zoom"]');
     await page.locator('#scene').scrollIntoViewIfNeeded();await page.locator('#scene').click({position:{x:50,y:35}});check(!(await page.evaluate(()=>JSON.parse(localStorage.getItem('peter-rabbit-progress-v1')).chapter1.found.length)),'Wrong scene point accepted');
     for(const target of data.findIt.targets){const h=target.hotspots[0];const box=await page.locator('#scene').boundingBox();await page.locator('#scene').click({position:{x:(h.x+h.w/2)*box.width/100,y:(h.y+h.h/2)*box.height/100}});await page.waitForTimeout(350);}
     await until(page,()=>JSON.parse(localStorage.getItem('peter-rabbit-progress-v1')).chapter1.stamps.includes(2),'Find it did not complete');
    }
    if(stage===3){
     for(const c of data.vocabulary.cards)await page.click(`[data-flip="${c.id}"]`);
     await page.click('[data-action="quiz-start"]');await screenshot('听音选图');
     for(let q=0;q<5;q++){const audio=await page.locator('.quiz-question [data-audio]').getAttribute('data-audio');await page.click(`[data-choice="${audio.slice(2)}"]`);await page.waitForFunction(expected=>document.querySelector('.quiz-count')?.textContent.startsWith(String(expected))||!document.querySelector('.quiz-count'),q+2);}
     await until(page,()=>JSON.parse(localStorage.getItem('peter-rabbit-progress-v1')).chapter1.stamps.includes(3),'Word quiz did not complete');
    }
    if(stage===4){
     await page.click('[data-action="translation"]');check(await page.locator('.lesson-line .zh').first().isHidden(),'Chinese translation did not hide');await page.click('[data-action="translation"]');
     await page.click('[data-action="lesson-auto"]');await until(page,()=>JSON.parse(localStorage.getItem('peter-rabbit-progress-v1')).chapter1.lessonHeard.length===10,'Lesson audio did not complete');
     await page.click('[data-role="PETER"]');for(let i=0;i<3;i++){await page.waitForSelector('[data-action="actor-next"]');check(await page.evaluate(()=>window.qaAudio.active.size===0),'Child line is not silent');await page.click('[data-action="actor-next"]');}
     await until(page,()=>JSON.parse(localStorage.getItem('peter-rabbit-progress-v1')).chapter1.stamps.includes(4),'Act it out did not complete');
    }
    if(stage===5){
     await page.click('[data-token="basket"]');await page.click('[data-slot="0"]');await page.click('[data-action="homework-check"]');check(!(await page.evaluate(()=>JSON.parse(localStorage.getItem('peter-rabbit-progress-v1')).chapter1.stamps.includes(5))),'Wrong homework accepted');
     for(const[i,word]of['garden','basket','blackberry','lettuce','radish'].entries()){await page.click(`[data-token="${word}"]`);await page.click(`[data-slot="${i}"]`);}
     await page.click('[data-action="homework-check"]');await page.waitForSelector('.completion');await screenshot('通关');
    }
   }
   const saved=await page.evaluate(()=>JSON.parse(localStorage.getItem('peter-rabbit-progress-v1')).chapter1);check(saved.stamps.length===5,'Not all five stamps saved');
   await page.reload();await page.click('#start');check(await page.locator('#reader-stamps .earned').count()===5,'Saved stamps not restored');
   // Restore homework review and exercise actual Pointer Events dragging.
   await page.click('[data-stage="5"]');await page.click('[data-action="homework-replay"]');await page.locator('.wordbox').scrollIntoViewIfNeeded();const from=await page.locator('[data-token="garden"]').boundingBox(),to=await page.locator('[data-slot="0"]').boundingBox();await page.mouse.move(from.x+from.width/2,from.y+from.height/2);await page.mouse.down();await page.mouse.move(to.x+to.width/2,to.y+to.height/2,{steps:10});await page.mouse.up();check((await page.textContent('[data-slot="0"]'))==='garden','Pointer drag did not fill the slot');
   await page.goto(`${base}/chapter.html?n=1&debug=1&stage=2`);await page.click('#start');await screenshot('热区核对');check(await page.locator('.hotspot').count()===13,'Debug hotspot count incorrect');
   await context.addInitScript(()=>{if(sessionStorage.getItem('qa-break')){const state=JSON.parse(localStorage.getItem('peter-rabbit-progress-v1'));state.chapter1.seconds=899;state.chapter1.reminded=false;localStorage.setItem('peter-rabbit-progress-v1',JSON.stringify(state));sessionStorage.removeItem('qa-break');}});await page.evaluate(()=>sessionStorage.setItem('qa-break','yes'));await page.reload();await page.click('#start');await page.waitForSelector('#rest-dialog[open]',{timeout:6000});await page.click('[data-close="rest-dialog"]');
   await page.click('#parent');await page.click('#reset');await page.click('#confirm-reset');check(await page.locator('#reader-stamps .earned').count()===0,'Parent reset failed');await page.click('[data-close="parent-dialog"]');
   const stats=await page.evaluate(()=>({maxActive:window.qaAudio.maxActive,micCalls:window.qaAudio.micCalls}));check(stats.maxActive<=1,'Overlapping audio sources');check(stats.micCalls===0,'Microphone requested');check(!errors.length,`Console/page errors: ${errors}`);check(!badResponses.length,`HTTP errors: ${badResponses}`);
   results.push({browser:browserName,device,status:'PASS',errors,badResponses,...stats});console.log(`PASS ${browserName} ${device}: five stages, stamps, quiz, role silence, drag, persistence, reset, break reminder, debug hotspots`);
  }catch(e){const state=await page.evaluate(()=>({feedback:document.querySelector('#feedback')?.textContent,progress:localStorage.getItem('peter-rabbit-progress-v1'),playing:[...document.querySelectorAll('.playing')].map(x=>x.dataset.audio),active:window.qaAudio.active.size,visibility:document.visibilityState}));results.push({browser:browserName,device,status:'FAIL',message:e.message,state,errors,badResponses});console.log(JSON.stringify(state));console.log(`FAIL ${browserName} ${device}: ${e.message}`);await screenshot('失败现场');}
  await context.close();
 }
 await browser.close();
}
await writeFile(resolve(out,'浏览器检查结果v1.0.json'),JSON.stringify({url:base,flowAudioPlaybackRate:1,results},null,2));
if(results.some(r=>r.status==='FAIL'))process.exitCode=1;
