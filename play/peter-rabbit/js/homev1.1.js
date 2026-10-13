import{readProgress,resetProgress,stampMarkup}from'./progressv1.1.js';
function renderStamps(){document.querySelectorAll('[data-chapter-stamps]').forEach(el=>el.innerHTML=stampMarkup(readProgress(Number(el.dataset.chapterStamps))));}
renderStamps();
window.addEventListener('pageshow',renderStamps);
window.addEventListener('storage',renderStamps);
const dialog=document.querySelector('#parent-dialog');document.querySelector('#parent').onclick=()=>dialog.showModal();document.querySelector('#parent-close').onclick=()=>dialog.close();
function cancelReset(){document.querySelector('#reset-confirm').hidden=true;document.querySelector('#reset').hidden=false;}
document.querySelector('#reset').onclick=()=>{document.querySelector('#reset-confirm').hidden=false;document.querySelector('#reset').hidden=true;document.querySelector('#confirm-reset').focus();};
document.querySelector('#cancel-reset').onclick=cancelReset;
document.querySelector('#confirm-reset').onclick=()=>{resetProgress();renderStamps();document.querySelector('#parent-feedback').textContent='已清除这台设备的四章进度。';cancelReset();};
dialog.addEventListener('close',cancelReset);
