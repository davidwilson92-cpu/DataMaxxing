function toggleNavigation(){const nav=document.querySelector('.app-nav'),button=document.querySelector('.mobile-menu-toggle');if(!nav||!button)return;const open=nav.classList.toggle('nav-open');button.setAttribute('aria-expanded',String(open));}
document.addEventListener('keydown',event=>{if(event.key==='Escape'&&document.querySelector('.app-nav.nav-open')){toggleNavigation();document.querySelector('.mobile-menu-toggle')?.focus();}});
document.querySelectorAll('input,textarea,select').forEach((node,index)=>{
  if(node.type==='hidden'||node.type==='checkbox')return;
  if(!node.id)node.id='field-'+(node.name||index);
  const label=node.previousElementSibling;if(label?.tagName==='LABEL'&&!label.htmlFor)label.htmlFor=node.id;
});
document.addEventListener('keydown',event=>{
  if(event.target.matches('[role=tab]')&&['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){
    const tabs=[...event.target.parentElement.querySelectorAll('[role=tab]')],at=tabs.indexOf(event.target);
    const next=event.key==='Home'?0:event.key==='End'?tabs.length-1:(at+(event.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length;
    event.preventDefault();tabs[next].click();document.querySelector('[role=tab][aria-selected=true]')?.focus();
  }
});
