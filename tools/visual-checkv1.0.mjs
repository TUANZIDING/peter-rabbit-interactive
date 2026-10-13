import{createRequire}from'node:module';
import{readFile,mkdir,writeFile}from'node:fs/promises';
import{resolve}from'node:path';
const require=createRequire(import.meta.url),{chromium,webkit,devices}=require(process.env.PETER_PLAYWRIGHT_MODULE||'playwright');
const root=resolve(import.meta.dirname,'..'),out=resolve(root,'reports/局部核对');await mkdir(out,{recursive:true});
// Approximate inner face regions labelled by eye in the source panels. These checks
// supplement visual review; they do not substitute for semantic image inspection.
const faces={
 2:[[[28,43,8,9],[59,31,9,13]],[[23,53,8,10],[64,37,8,11]],[[23,48,9,13]],[[48,27,13,15]],[[47,57,9,11],[22,28,7,7],[55,24,7,7],[82,38,6,7]],[[91,73,7,9],[73,42,8,10]]],
 3:[[[45,42,7,8]],[[22,51,6,9],[66,34,9,12]],[[33,48,10,13],[64,44,10,14]],[[79,40,7,12],[26,38,9,13]],[[24,51,9,14],[72,54,9,14]],[[25,52,9,13],[76,27,8,9]]],
 4:[[[27,53,7,9]],[[57,49,9,11]],[[65,67,7,9],[14,23,5,7]],[[65,40,9,12]],[[18,70,8,10],[79,35,10,13]],[[8,49,9,12],[27,24,9,12],[62,50,8,10],[78,50,8,10],[93,51,6,10]]]
};
const results=[];
for(const[name,type]of[['Chromium',chromium],['WebKit',webkit]]){
 const browser=await type.launch();
 for(const[device,options]of[['iPhone13',devices['iPhone 13']],['iPad',{...devices['iPad (gen 7)'],viewport:{width:810,height:1080}}],['desktop',{viewport:{width:1440,height:1000}}]]){
  const context=await browser.newContext({...options,reducedMotion:'reduce'}),page=await context.newPage();
  for(const n of[2,3,4]){
   const data=JSON.parse(await readFile(resolve(root,`play/peter-rabbit/data/ch0${n}v1.0.json`),'utf8'));
   await page.goto(`http://127.0.0.1:8817/play/peter-rabbit/chapter.html?n=${n}`);await page.click('#start');await page.waitForSelector('#start-dialog',{state:'hidden'});await page.evaluate(()=>document.fonts.ready);
   const inspect=async(frame,regions,label)=>{
    await frame.scrollIntoViewIfNeeded();await frame.locator('img').evaluate(img=>img.decode());
    const defects=await frame.evaluate((el,regions)=>{const r=el.getBoundingClientRect();return [...el.querySelectorAll('.bubble,.hw-bubble')].flatMap(b=>{const q=b.getBoundingClientRect();const box={x:(q.x-r.x)/r.width*100,y:(q.y-r.y)/r.height*100,w:q.width/r.width*100,h:q.height/r.height*100};return regions.filter(([x,y,w,h])=>box.x<x+w&&box.x+box.w>x&&box.y<y+h&&box.y+box.h>y).map(face=>({bubble:b.dataset.id||'homework',box,face}));});},regions);
    await frame.screenshot({path:resolve(out,`ch${n}-${name}-${device}-${label}v1.0.png`)});
    results.push({chapter:n,browser:name,device,label,faceIntersections:defects});
   };
   for(let i=0;i<6;i++)await inspect(page.locator('.panel-frame').nth(i),faces[n][i],`漫画${i+1}`);
   await page.click('[data-stage="4"]');await page.locator('.theater-card .panel-frame').screenshot({path:resolve(out,`ch${n}-${name}-${device}-剧场v1.0.png`)});
   await page.click('[data-stage="5"]');
   const expected=data.homework.panels.flatMap(h=>h.answers),tokens=expected.map(w=>Object.entries(data.homework.forms).find(([k,v])=>v===w.toLowerCase())?.[0]||w.toLowerCase());
   for(const[i,token]of tokens.entries()){await page.click(`[data-token="${token}"]`);await page.click(`[data-slot="${i}"]`);}
   for(let i=0;i<4;i++)await inspect(page.locator('.hw-picture').nth(i),faces[n][Number(data.homework.panels[i].panel.slice(1))-1],`填词${i+1}`);
  }
  await context.close();
 }
 await browser.close();
}
await writeFile(resolve(out,'脸部核对结果v1.0.json'),JSON.stringify(results,null,2));
console.log(JSON.stringify(results.filter(r=>r.faceIntersections.length),null,2));
