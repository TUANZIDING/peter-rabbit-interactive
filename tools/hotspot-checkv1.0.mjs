import{createRequire}from'node:module';import{readFile,mkdir,writeFile}from'node:fs/promises';import{resolve}from'node:path';
const require=createRequire(import.meta.url),{chromium}=require(process.env.PETER_PLAYWRIGHT_MODULE||'playwright');
const root=resolve(import.meta.dirname,'..'),out=resolve(root,'reports/四章检查');await mkdir(out,{recursive:true});
const browser=await chromium.launch(),context=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce'}),page=await context.newPage(),results=[];
const datasets=await Promise.all([1,2,3,4].map(async n=>JSON.parse(await readFile(resolve(root,`play/peter-rabbit/data/ch0${n}v1.0.json`),'utf8'))));
await context.addInitScript(datasets=>{const q=new URLSearchParams(location.search),n=Number(q.get('n')),target=Number(q.get('qa-target'));if(!q.has('qa-target'))return;const chapter=datasets.find(d=>d.chapter.number===n);localStorage.setItem('peter-rabbit-progress-v1',JSON.stringify({version:1,[`chapter${n}`]:{stamps:[],heard:[],found:chapter.findIt.targets.slice(0,target).map(t=>t.id),cards:[],quizDone:false,lessonHeard:[],actDone:false,seconds:0,reminded:false}}));},datasets);
for(const data of datasets){const n=data.chapter.number;
 for(const[index,target]of data.findIt.targets.entries())for(const[area,h]of target.hotspots.entries()){
  await page.goto(`http://127.0.0.1:8817/play/peter-rabbit/chapter.html?n=${n}&stage=2&qa-target=${index}`);await page.click('#start');await page.waitForSelector('#start-dialog',{state:'hidden'});await page.locator('#scene img').evaluate(i=>i.decode());
  const box=await page.locator('#scene').boundingBox();await page.locator('#scene').click({position:{x:(h.x+h.w/2)*box.width/100,y:(h.y+h.h/2)*box.height/100}});
  const accepted=await page.evaluate(({n,id})=>JSON.parse(localStorage.getItem('peter-rabbit-progress-v1'))[`chapter${n}`].found.includes(id),{n,id:target.id});results.push({chapter:n,target:target.id,area:area+1,accepted});if(!accepted)throw new Error(`Missed chapter ${n} / ${target.id} / ${area+1}`);
 }
}
await context.close();await browser.close();await writeFile(resolve(out,'全部热区点击结果v1.0.json'),JSON.stringify(results,null,2));console.log(`PASS: all ${results.length} hotspot centres accepted, including alternate objects and cropped scene coordinates.`);
