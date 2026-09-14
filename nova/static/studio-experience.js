/* Persistent canvas: customer work stays separate from assistant conversation. */
let canvasMode='edit';
let publicationStates={};
const connectionData=JSON.parse(document.getElementById('studioConnections').textContent);
function studioView(view){
  document.querySelector('.conversation-layout').dataset.view=view;
  document.querySelectorAll('[data-studio-view]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.studioView===view)));
}
function canvasView(mode){
  canvasMode=mode;
  document.getElementById('canvasEditor').hidden=mode!=='edit';
  document.getElementById('canvasPreview').hidden=mode==='edit';
  document.querySelectorAll('[data-canvas-mode]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.canvasMode===mode)));
  renderCanvasPreview();studioView(mode==='edit'?'draft':'preview');
}
function renderCanvas(markup){
  document.getElementById('canvasEditor').innerHTML=markup;
  document.getElementById('ideaTitle').textContent=lastBrief||'Your next idea';
  renderCanvasPreview();renderReadiness();
}
const formatNotes={x:'A single post or ordered thread. Each post must fit the platform limit.',instagram:'A caption for your image or video. Zova has not created the visual.',facebook:'Post text with your selected link or media.',tiktok:'A caption for your uploaded video. This is not a generated video.'};
function renderCanvasPreview(){
  const platforms=canvasMode==='compare'?Object.keys(variants):[currentPlatform].filter(p=>variants[p]);
  document.getElementById('canvasPreview').innerHTML=platforms.length?`<p class="preview-disclaimer">Content preview — layout is approximate. Final review confirms the exact destination, text, media and settings.</p><div class="version-previews">${platforms.map(p=>`<article class="version-preview"><h3>${platformName(p)}</h3><p class="format-note">${formatNotes[p]}</p>${variants[p].posts.map((text,i)=>`<div class="preview-post"><small>${variants[p].posts.length>1?'Post '+(i+1):'Post text'}</small><p>${esc(text)}</p></div>`).join('')}<div class="review-media">${uploadedMedia.map(mediaPreview).join('')}</div>${document.getElementById('linkUrl').value?`<p class="preview-link">Source: ${esc(document.getElementById('linkUrl').value)}</p>`:''}</article>`).join('')}</div>`:'<p>Your platform previews will appear here after you create a draft.</p>';
}
function renderReadiness(){
  const platforms=selectedPlatforms();
  document.getElementById('destinationReadiness').innerHTML=platforms.map(p=>{
    const accounts=connectionData[p]||[];
    const missing=['instagram','tiktok'].includes(p)&&!uploadedMedia.length;
    return `<li><b>${platformName(p)}</b><span>${accounts.length?accounts.map(a=>esc(a)).join(', '):'Draft only · connect before publishing'}${missing?' · '+(p==='tiktok'?'Video':'Media')+' required':''}</span></li>`;
  }).join('')||'<li>Choose platforms for your versions.</li>';
  document.getElementById('threadLength').hidden=!platforms.includes('x');
}
function openReview(){studioView('draft');document.getElementById('reviewPanel').scrollIntoView({block:'nearest',behavior:'smooth'});}
function publicationStatus(status){return {unknown:'Outcome unconfirmed — check the destination; do not resend until resolved',pending:'Waiting for platform processing',publishing:'Sending — awaiting a result',scheduled:'Scheduled',published:'Published',failed:'Failed — review before retrying',cancelled:'Cancelled'}[status]||status;}
function downloadWorkspace(){
  const blob=new Blob([JSON.stringify(draftPayload(),null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');
  a.href=url;a.download='zova-unsaved-workspace.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
async function compareSaved(){
  if(!currentDraftId)return;
  const id=currentDraftId;
  try{const row=await api(`/api/drafts/${id}`);if(id!==currentDraftId)return;
    document.getElementById('saveComparison').innerHTML=`<h3>Saved version compared with this tab</h3><p>Your current work remains in the editor. Download it before choosing to reload.</p><div class="version-previews">${[['This tab',draftPayload()],['Saved on Zova',row]].map(([label,data])=>`<article class="version-preview"><h4>${label}</h4><p>${esc(data.workspace?.composer||'')}</p>${Object.entries(data.variants||{}).map(([p,v])=>`<h4>${platformName(p)}</h4>${v.posts.map(t=>`<p class="review-copy">${esc(t)}</p>`).join('')}`).join('')}</article>`).join('')}</div><button type="button" onclick="downloadWorkspace()">Download this tab’s work</button><a href="/studio?draft=${id}">Reload saved version (discards this tab’s changes)</a>`;
    openReview();
  }catch(error){document.getElementById('saveComparison').textContent=error.message;}
}
document.querySelectorAll('.platform-check input').forEach(node=>node.addEventListener('change',renderReadiness));

let textHistory=[];
function rememberTextRevision(){
  if(!editableDraft()||!Object.keys(variants).length)return;
  const snapshot=JSON.stringify(variants);
  if(JSON.stringify(textHistory.at(-1))!==snapshot)textHistory.push(JSON.parse(snapshot));
  textHistory=textHistory.slice(-3);
}
function undoTextEdit(){
  if(sendingMessage||!editableDraft())return;
  while(textHistory.length&&JSON.stringify(textHistory.at(-1))===JSON.stringify(variants))textHistory.pop();
  if(!textHistory.length){document.getElementById('undoStatus').textContent='No earlier text edit is available.';return;}
  variants=textHistory.pop();if(!variants[currentPlatform])currentPlatform=Object.keys(variants)[0];
  renderCanvas(draftWorkspace());canvasView('edit');scheduleAutosave();
  document.getElementById('undoStatus').textContent='Previous text restored. Media and source are unchanged.';
}

document.getElementById('canvasEditor').addEventListener('keydown',event=>{
  const tab=event.target.closest('[role=tab]');
  if(!tab||!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
  const tabs=[...document.querySelectorAll('.draft-tab')],index=tabs.indexOf(tab);
  const next=event.key==='Home'?0:event.key==='End'?tabs.length-1:(index+(event.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length;
  event.preventDefault();tabs[next].click();
});
