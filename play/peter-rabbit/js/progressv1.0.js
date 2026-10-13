const KEY='peter-rabbit-progress-v1';
const empty=()=>({stamps:[],heard:[],found:[],cards:[],quizDone:false,lessonHeard:[],actDone:false,seconds:0,reminded:false});
export let persistenceAvailable=true;
export function readProgress(){try{const d=JSON.parse(localStorage.getItem(KEY)||'null');return d?.version===1?{...empty(),...d.chapter1}:empty();}catch{persistenceAvailable=false;return empty();}}
export function saveProgress(p){try{localStorage.setItem(KEY,JSON.stringify({version:1,chapter1:p}));}catch{persistenceAvailable=false;}}
export function resetProgress(){const p=empty();saveProgress(p);return p;}
export function stampMarkup(p){return [1,2,3,4,5].map(n=>`<span class="stamp ${p.stamps.includes(n)?'earned':''}" aria-label="第${n}关${p.stamps.includes(n)?'已完成':'待完成'}">${p.stamps.includes(n)?'✓':n}</span>`).join('');}
