/* Keep linked settings and save errors reachable inside the grouped account. */
function revealAccountSection(){
 let target;
 try{target=document.getElementById(decodeURIComponent(location.hash.slice(1)));}catch(_){return;}
 if(!target)return;
 for(let parent=target;parent;parent=parent.parentElement){
  if(parent.tagName==='DETAILS')parent.open=true;
 }
 target.scrollIntoView({block:'start'});
}
window.addEventListener('hashchange',revealAccountSection);
revealAccountSection();
