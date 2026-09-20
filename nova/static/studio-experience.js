/* Chat presentation; persistence and immutable approval remain separate. */
const instagramFormat=()=>document.getElementById('instagramFormat').value;
const instagramLabel=()=>instagramFormat()==='story'?'Story':uploadedMediaKind==='video'?'Reel · shared to feed':'Post · feed';
const instagramNote=()=>instagramFormat()==='story'?'One image or video, visible for 24 hours. Only the visual publishes: draft text is planning notes, not an overlay or caption. Add any text to your file first. Business account required.':'An image publishes to your feed. A video publishes as a Reel shared to your feed.';
function instagramInstruction(platform,instruction){return platform==='instagram'&&instagramFormat()==='story'?instruction+'\nFor Instagram only: write concise Story planning copy for one visual, not a feed caption or hashtags. Text is a separate planning note; do not claim it is added to the uploaded visual.':instruction;}
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
  if (typeof contextualRefinements === 'function') contextualRefinements();
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
function sizeComposer(){const input=document.getElementById('brief');input.style.height='auto';input.style.height=Math.min(input.scrollHeight,Math.min(112,window.innerHeight*0.18))+'px';if(!sendingMessage)document.getElementById('generateBtn').disabled=!input.value.trim()||!editableDraft();}
const formatNotes={x:'A single post or ordered thread. Each post must fit the platform limit.',instagram:'A caption for your image or video. Zova has not created the visual.',facebook:'Post text with your selected link or media.',tiktok:'A caption for your uploaded video. This is not a generated video.'};
function renderCanvasPreview(){
  if(!document.getElementById('canvasPreview'))return;
  const platforms=canvasMode==='compare'?Object.keys(variants):[currentPlatform].filter(p=>variants[p]);
  document.getElementById('canvasPreview').innerHTML=platforms.length?`<button class="quiet-button" onclick="canvasView('edit');finishEditing()">← Back to draft</button><p class="preview-disclaimer">Preview · final review confirms the exact account, content and settings.</p><div class="version-previews">${platforms.map(p=>`<article class="version-preview"><h3>${platformName(p)}${p==='instagram'?' · '+instagramLabel():''}</h3><p class="format-note">${p==='instagram'?instagramNote():formatNotes[p]}</p>${variants[p].posts.map((text,i)=>`<div class="preview-post"><small>${variants[p].posts.length>1?'Post '+(i+1):p==='instagram'&&instagramFormat()==='story'?'Planning notes · not published':'Post text'}</small><p>${esc(text)}</p></div>`).join('')}<div class="review-media">${uploadedMedia.map(mediaPreview).join('')}</div>${document.getElementById('linkUrl').value?`<p class="preview-link">Source: ${esc(document.getElementById('linkUrl').value)}</p>`:''}</article>`).join('')}</div>`:'<p>Your platform previews will appear here after you create a draft.</p>';
}
function renderReadiness(){
  const platforms=selectedPlatforms();
  document.getElementById('destinationReadiness').innerHTML=platforms.map(p=>{
    const accounts=connectionData[p]||[];
    const missing=['instagram','tiktok'].includes(p)&&!uploadedMedia.length;
    return `<li><b>${platformName(p)}</b><span>${accounts.length?accounts.map(a=>esc(a)).join(', '):'Draft only · connect before publishing'}${missing?' · '+(p==='tiktok'?'Video':'Media')+' required':''}</span></li>`;
  }).join('')||'<li>Choose platforms for your versions.</li>';
  document.getElementById('xFormat').hidden=!platforms.includes('x');
  document.getElementById('instagramFormatControl').hidden=!platforms.includes('instagram');
  document.getElementById('instagramFormat').disabled=!platforms.includes('instagram')||sendingMessage||!editableDraft();
  const hint=document.getElementById('instagramFormatHint');hint.hidden=!platforms.includes('instagram');hint.textContent=instagramFormat()==='story'?'24-hour Story · only your visual publishes. Add any text to your file first.':instagramNote();
  document.querySelectorAll('.composer-platforms input').forEach(input=>{input.closest('.platform-check').classList.toggle('is-selected',input.checked);input.closest('.platform-check').classList.toggle('is-connected',Boolean(connectionData[input.value]?.length));input.title=connectionData[input.value]?.length?'Connected':'Connect to publish; drafting is available';});
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
document.querySelectorAll('.platform-check input').forEach(node=>node.addEventListener('change',()=>{renderReadiness();if(node.checked&&!connectionData[node.value]?.length){connectionPlatform=node.value;document.getElementById('connectionTitle').textContent='Connect '+platformName(node.value);document.getElementById('connectionDescription').textContent='Select your '+platformName(node.value)+' account to publish there. You can also keep writing a draft without connecting yet.';document.getElementById('connectionPrompt').showModal();}}));

document.getElementById('instagramFormat').addEventListener('change',()=>{renderReadiness();refreshDraft();});
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

let connectionPlatform=null;
async function connectSelectedPlatform(button){
  if(!connectionPlatform)return;
  button.disabled=true;
  try{await saveDraftNow();location.href='/connect/'+encodeURIComponent(connectionPlatform);}
  catch(error){document.getElementById('connectionDescription').textContent='Your work could not be saved. Close this prompt and retry saving before connecting.';button.disabled=false;}
}
let recentPosts=[];
let historyRequest=0;
function renderRecentPosts(){
  const rows=recentPosts.slice(0,20);
  document.querySelectorAll('.recent-posts').forEach(nav=>{nav.innerHTML=rows.length?rows.map(row=>`<a href="/studio?draft=${row.id}" ${Number(currentDraftId)===row.id?'aria-current="page"':''} onclick="openSavedPost(event,${row.id})"><span>${esc(row.title||row.brief||'Untitled conversation')}</span><small>${esc(row.status==='draft'?'Draft':publicationStatus(row.status))}</small></a>`).join(''):'<p>Your conversations and drafts will appear here as you write.</p>';});
}
async function loadRecentPosts(){
  const request=++historyRequest;
  try{const rows=await api('/api/drafts');if(request!==historyRequest)return;recentPosts=rows;renderRecentPosts();}
  catch{document.querySelectorAll('.recent-posts').forEach(nav=>{nav.innerHTML='<p>Could not load saved posts.</p><button class="quiet-button" onclick="loadRecentPosts()">Retry</button>';});}
}
function rememberSavedPost(){
  if(!currentDraftId)return;
  historyRequest++;
  const title=lastBrief||conversation.find(m=>m.role==='user')?.content||document.getElementById('brief').value||'Untitled conversation';
  recentPosts=[{id:Number(currentDraftId),title:title.slice(0,100),status:currentDraftStatus},...recentPosts.filter(r=>r.id!==Number(currentDraftId))];renderRecentPosts();
}
async function openSavedPost(event,id){
  if(event.ctrlKey||event.metaKey||event.shiftKey||event.altKey)return;
  event.preventDefault();if(sendingMessage||mediaUploading||studioLoading)return;
  try{await saveDraftNow();location.href='/studio?draft='+id;}
  catch{document.getElementById('navigationDialog').close();document.getElementById('undoStatus').textContent='Save this conversation before opening another. Retry save or download your work.';}
}
window.addEventListener('DOMContentLoaded',loadRecentPosts);
