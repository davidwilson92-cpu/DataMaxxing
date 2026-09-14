/* Chat presentation; persistence and immutable approval remain separate. */
let canvasMode='edit';
let editingDraft=false;
let publicationStates={};
const connectionData=JSON.parse(document.getElementById('studioConnections').textContent);
function studioView(){document.getElementById('postSettings').close();}
function threadHost(id){let node=document.getElementById(id);if(!node){node=document.createElement('section');node.id=id;document.getElementById('chatFeed').append(node);}return node;}
function reviewHost(){return threadHost('reviewPanel');}
function renderCanvas(markup){
  let turn=document.getElementById('draftResponse');
  if(!turn){turn=document.createElement('article');turn.id='draftResponse';turn.className='draft-response';turn.setAttribute('aria-label','Current draft');}
  document.getElementById('chatFeed').append(turn);
  turn.innerHTML='<div id="canvasEditor"></div><div id="canvasPreview" hidden></div>';
  document.getElementById('canvasEditor').innerHTML=markup;
  renderReadiness();
}
function canvasView(mode){
  canvasMode=mode;
  if(mode==='edit'){editingDraft=true;refreshDraft();}
  const editor=document.getElementById('canvasEditor'),preview=document.getElementById('canvasPreview');
  if(!editor||!preview)return;
  editor.hidden=mode!=='edit';preview.hidden=mode==='edit';
  renderCanvasPreview();
  (mode==='edit'?editor.querySelector('textarea'):preview.querySelector('button'))?.focus();
}
function finishEditing(){editingDraft=false;refreshDraft();document.querySelector('#canvasEditor .response-actions button')?.focus();saveDraftNow().catch(()=>{});}
async function copyDraft(button){try{await navigator.clipboard.writeText((variants[currentPlatform]?.posts||[]).join('\n\n'));button.textContent='Copied';}catch{document.getElementById('undoStatus').textContent='Select the draft text to copy it.';}}
function sizeComposer(){const input=document.getElementById('brief');input.style.height='auto';input.style.height=Math.min(input.scrollHeight,180)+'px';if(!sendingMessage)document.getElementById('generateBtn').disabled=!input.value.trim()||!editableDraft();}
const formatNotes={x:'A single post or ordered thread. Each post must fit the platform limit.',instagram:'A caption for your image or video. Zova has not created the visual.',facebook:'Post text with your selected link or media.',tiktok:'A caption for your uploaded video. This is not a generated video.'};
function renderCanvasPreview(){
  if(!document.getElementById('canvasPreview'))return;
  const platforms=canvasMode==='compare'?Object.keys(variants):[currentPlatform].filter(p=>variants[p]);
  document.getElementById('canvasPreview').innerHTML=platforms.length?`<button class="quiet-button" onclick="canvasView('edit');finishEditing()">← Back to draft</button><p class="preview-disclaimer">Preview · final review confirms the exact account, content and settings.</p><div class="version-previews">${platforms.map(p=>`<article class="version-preview"><h3>${platformName(p)}</h3><p class="format-note">${formatNotes[p]}</p>${variants[p].posts.map((text,i)=>`<div class="preview-post"><small>${variants[p].posts.length>1?'Post '+(i+1):'Post text'}</small><p>${esc(text)}</p></div>`).join('')}<div class="review-media">${uploadedMedia.map(mediaPreview).join('')}</div>${document.getElementById('linkUrl').value?`<p class="preview-link">Source: ${esc(document.getElementById('linkUrl').value)}</p>`:''}</article>`).join('')}</div>`:'<p>Your platform previews will appear here after you create a draft.</p>';
}
function renderReadiness(){
  const platforms=selectedPlatforms();
  document.getElementById('destinationReadiness').innerHTML=platforms.map(p=>{
    const accounts=connectionData[p]||[];
    const missing=['instagram','tiktok'].includes(p)&&!uploadedMedia.length;
    return `<li><b>${platformName(p)}</b><span>${accounts.length?accounts.map(a=>esc(a)).join(', '):'Draft only · connect before publishing'}${missing?' · '+(p==='tiktok'?'Video':'Media')+' required':''}</span></li>`;
  }).join('')||'<li>Choose platforms for your versions.</li>';
  document.getElementById('postSettingsButton').textContent=platforms.length===1?platformName(platforms[0]):'Platforms · '+platforms.length;
  document.getElementById('threadLength').disabled=!platforms.includes('x')||sendingMessage||!editableDraft();
}
function openReview(){document.getElementById('postSettings').close();const host=reviewHost();document.getElementById('chatFeed').append(host);host.scrollIntoView({block:'start',behavior:'smooth'});const heading=host.querySelector('.chat-confirmation:last-child h3');if(heading){heading.tabIndex=-1;heading.focus({preventScroll:true});}}
function publicationStatus(status){return {unknown:'Outcome unconfirmed — check the destination; do not resend until resolved',pending:'Waiting for platform processing',publishing:'Sending — awaiting a result',scheduled:'Scheduled',published:'Published',failed:'Failed — review before retrying',cancelled:'Cancelled'}[status]||status;}
function downloadWorkspace(){
  const blob=new Blob([JSON.stringify(draftPayload(),null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');
  a.href=url;a.download='zova-unsaved-workspace.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
async function compareSaved(){
  if(!currentDraftId)return;
  const id=currentDraftId;
  try{const row=await api(`/api/drafts/${id}`);if(id!==currentDraftId)return;
    threadHost('saveComparison').innerHTML=`<h3>Saved version compared with this tab</h3><p>Your current work remains in the editor. Download it before choosing to reload.</p><div class="version-previews">${[['This tab',draftPayload()],['Saved on Zova',row]].map(([label,data])=>`<article class="version-preview"><h4>${label}</h4><p>${esc(data.workspace?.composer||'')}</p>${Object.entries(data.variants||{}).map(([p,v])=>`<h4>${platformName(p)}</h4>${v.posts.map(t=>`<p class="review-copy">${esc(t)}</p>`).join('')}`).join('')}</article>`).join('')}</div><button type="button" onclick="downloadWorkspace()">Download this tab’s work</button><a href="/studio?draft=${id}">Reload saved version (discards this tab’s changes)</a>`;
    threadHost('saveComparison').scrollIntoView({block:'start'});
  }catch(error){threadHost('saveComparison').textContent=error.message;}
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
  editingDraft=false;renderCanvas(draftWorkspace());scheduleAutosave();
  document.getElementById('undoStatus').textContent='Previous text restored. Media and source are unchanged.';
}

document.getElementById('brief').addEventListener('input',sizeComposer);
document.querySelectorAll('dialog').forEach(dialog=>dialog.addEventListener('click',event=>{if(event.target===dialog){const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dialog.close();}}));

function fitVisibleViewport(){const view=window.visualViewport;document.querySelector('.conversation-workspace').style.setProperty('--chat-height',view&&window.innerWidth<761?view.height+'px':'100dvh');}
window.visualViewport?.addEventListener('resize',fitVisibleViewport);
window.addEventListener('resize',fitVisibleViewport);
fitVisibleViewport();
