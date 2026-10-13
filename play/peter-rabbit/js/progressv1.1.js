// Keep the original key and chapter1 shape so a family's existing stamps survive.
const KEY='peter-rabbit-progress-v1';
const empty=()=>({stamps:[],heard:[],found:[],cards:[],quizDone:false,lessonHeard:[],actDone:false,seconds:0,reminded:false});
export let persistenceAvailable=true;
function readStore(){try{const d=JSON.parse(localStorage.getItem(KEY)||'null');return d?.version===1?d:{version:1};}catch{persistenceAvailable=false;return {version:1};}}
export function readProgress(chapter=1){return {...empty(),...readStore()[`chapter${chapter}`]};}
function chaptersWithCurrent(current,chapter){const store=readStore();return [1,2,3,4].map(n=>n===chapter?current:{...empty(),...store[`chapter${n}`]});}
export function totalSeconds(current,chapter){return chaptersWithCurrent(current,chapter).reduce((sum,p)=>sum+Math.max(0,Number(p.seconds)||0),0);}
export function restReminded(current,chapter){return chaptersWithCurrent(current,chapter).some(p=>p.reminded);}
export function saveProgress(p,chapter=1){try{const d=readStore();d[`chapter${chapter}`]=p;localStorage.setItem(KEY,JSON.stringify(d));}catch{persistenceAvailable=false;}}
export function resetProgress(chapter=1){try{localStorage.removeItem(KEY);}catch{persistenceAvailable=false;}return empty();}
export function stampMarkup(p){return [1,2,3,4,5].map(n=>`<span class="stamp ${p.stamps.includes(n)?'earned':''}" aria-label="第${n}关${p.stamps.includes(n)?'已完成':'待完成'}">${p.stamps.includes(n)?'✓':n}</span>`).join('');}
