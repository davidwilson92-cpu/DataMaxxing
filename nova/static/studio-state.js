/* Persistence and conversation lifecycle. The editor/sidebar remain in studio.js. */
let draftRevision = 0;
let changeSerial = 0;
let savedSerial = 0;
let sendingMessage = false;
let studioLoading = true;
let saveLabel = 'Saved';
const editableDraft = () => ['draft','failed','partial','cancelled'].includes(currentDraftStatus);

function setAutosaveStatus(text){
  saveLabel=text;
  document.getElementById("saveRecovery").hidden=!/failed|conflict|retry/i.test(text);
  document.querySelectorAll('[data-save-status],#autosaveStatus').forEach(node=>node.textContent=text);
}
let reviewEpoch=0;
function invalidateReview(){reviewEpoch++;pendingReview=null;document.querySelectorAll('.chat-confirmation').forEach(node=>node.remove());}
function addAssistantMessage(text,extra=''){
  const follow=stickToLatest;
  conversation.push({role:'assistant',content:text});
  document.getElementById('chatFeed').insertAdjacentHTML('beforeend',`<article class="chat-message assistant-message"><div class="assistant-avatar">Z</div><div class="message-content"><div class="message-name">Zova</div><p>${esc(text)}</p></div></article>`);
  if(extra){editingDraft=false;renderCanvas(draftWorkspace());}
  if(extra&&follow)document.getElementById('draftResponse').scrollIntoView({block:'nearest'});else scrollChat();
}
function draftPayload(){
  return {brief:lastBrief,instruction:'',platforms:Object.keys(variants),variants,revision:draftRevision,thread_length:+document.getElementById('threadLength').value,
    workspace:{instagram_format:instagramFormat(),media_asset_ids:uploadedMediaIds,video_duration:uploadedVideoDuration,link_url:document.getElementById('linkUrl').value,
      conversation,text_history:textHistory,composer:document.getElementById('brief').value,selected_platforms:selectedPlatforms(),active_platform:currentPlatform}};
}
function scheduleAutosave(){
  if(studioLoading || !editableDraft())return;
  changeSerial++; invalidateReview();setAutosaveStatus('Unsaved changes');
  clearTimeout(autosaveTimer);
  autosaveTimer=setTimeout(()=>saveDraftNow().catch(()=>{}),650);
}
async function saveDraftNow(){
  clearTimeout(autosaveTimer);autosaveTimer=null;
  if(studioLoading || !editableDraft())return;
  if(autosaveInFlight){await autosaveInFlight;if(savedSerial!==changeSerial)return saveDraftNow();return;}
  if(savedSerial===changeSerial && currentDraftId)return;
  if(!currentDraftId && !conversation.some(message=>message.role==='user') && !Object.keys(variants).length && !document.getElementById('brief').value && !uploadedMedia.length && !document.getElementById('linkUrl').value && changeSerial===0)return;
  autosaveInFlight=(async()=>{
    setAutosaveStatus('Saving…');
    if(!currentDraftId){
      const row=await api('/api/drafts',{method:'POST',headers,body:'{}'});
      currentDraftId=row.id;draftRevision=row.revision;
      history.replaceState({},'',window.zovaWorkspaceUrl(`/studio?draft=${row.id}`));
    }
    const serial=changeSerial,id=currentDraftId,payload=JSON.stringify(draftPayload());
    const result=await api(`/api/drafts/${id}`,{method:'PATCH',headers,body:payload});
    draftRevision=result.revision;savedSerial=serial;
    setAutosaveStatus(savedSerial===changeSerial?'Saved':'Unsaved changes');rememberSavedPost();
  })();
  try{await autosaveInFlight;}catch(error){setAutosaveStatus(error.status===409?'Save conflict — compare versions':'Save failed — retry');throw error;}
  finally{autosaveInFlight=null;}
  if(savedSerial!==changeSerial)return saveDraftNow();

}
function refreshDraft(){
  const card=document.querySelector('[data-current-draft]');if(!card)return;
  const feed=document.getElementById('chatFeed'),top=feed.scrollTop;
  card.outerHTML=draftWorkspace();renderCanvasPreview();renderReadiness();setAutosaveStatus(saveLabel);feed.scrollTop=top;
}
function switchPlatform(platform){
  if(sendingMessage)return;
  currentPlatform=platform;refreshDraft();scheduleAutosave();
  document.querySelector('.draft-tab.active')?.focus();
}
function updateDraftPost(platform,index,value){
  if(!editableDraft() || sendingMessage || !variants[platform])return;
  variants[platform].posts[index]=value;
  const count=document.querySelectorAll('[data-character-count]')[index];if(count)count.textContent=value.length;
  scheduleAutosave();
}
function promptComposer(text){studioView('chat');const input=document.getElementById('brief');input.value=text;input.focus();input.setSelectionRange(text.length,text.length);sizeComposer();scheduleAutosave();}
function studioBusy(active){
  sendingMessage=active;
  document.getElementById('generateBtn').disabled=active||!editableDraft()||!document.getElementById('brief').value.trim();
  document.getElementById('brief').readOnly=active||!editableDraft();
  document.getElementById('newChatBtn').disabled=active;
  document.querySelectorAll('#variantEditor textarea').forEach(node=>node.readOnly=active||!editableDraft());
  document.querySelectorAll('.platform-check input,#threadLength,#instagramFormat,#linkUrl,#mediaInput').forEach(node=>node.disabled=active||!editableDraft());
}
async function sendMessage(){
  const input=document.getElementById('brief'),text=input.value.trim();
  if(!text||sendingMessage||studioLoading||mediaUploading||!editableDraft())return;
  studioBusy(true);invalidateReview();
  try{
    await saveDraftNow();
    const plan=await api('/api/conversation/plan',{method:'POST',headers,body:JSON.stringify({message:text,draft_id:currentDraftId,selected_platforms:selectedPlatforms(),active_platform:currentPlatform,recent_messages:conversation.slice(-12)})});
    stickToLatest=true;addUserMessage(text);scrollChat(true);input.value='';sizeComposer();changeSerial++;addThinking();
    if(plan.action==='answer'){removeThinking();addAssistantMessage(plan.reply||'What would you like to create or change?');}
    else if(plan.action==='insight'){
      const result=await api('/api/insights',{method:'POST',headers,body:JSON.stringify({question:text})});removeThinking();addAssistantMessage(result.answer);
    }else if(plan.action==='publish'||plan.action==='schedule'){
      removeThinking();await saveDraftNow();
      if(!Object.keys(variants).length)addAssistantMessage('Create a draft first, then review it before publishing.');
      else if(plan.action==='publish')await requestPublishConfirmation('publish');else await suggestSchedule(text);
    }else if(plan.action==='rewrite'){
      const targets=plan.platforms.length?plan.platforms:[currentPlatform],changed={};
      for(const p of targets){
        if(!variants[p])throw new Error(`Add a ${platformName(p)} version first.`);
        const result=await api('/api/ai/rewrite',{method:'POST',headers,body:JSON.stringify({platform:p,posts:variants[p].posts,action:'',instruction:instagramInstruction(p,text)})});
        changed[p]={posts:result.posts};
      }
      rememberTextRevision();Object.assign(variants,changed);currentPlatform=targets[0];removeThinking();addAssistantMessage('Updated the requested versions. Here’s the updated version.',draftWorkspace());
    }else{
      const platforms=plan.platforms.length?plan.platforms:selectedPlatforms();
      if(!platforms.length)throw new Error('Choose at least one platform.');
      if(!validateVideoPlatforms(platforms))throw new Error('Videos can only be used with Instagram and TikTok.');
      if(plan.action==='create' && Object.keys(variants).length){
        await saveDraftNow();const row=await api('/api/drafts',{method:'POST',headers,body:'{}'});
        currentDraftId=row.id;draftRevision=row.revision;variants={};textHistory=[];publicationStates={};lastBrief=text;renderCanvas('<p>Creating your new versions…</p>');history.replaceState({},'',window.zovaWorkspaceUrl(`/studio?draft=${row.id}`));
      }
      const targets=plan.action==='add_platforms'?platforms.filter(p=>!variants[p]):platforms;
      if(!targets.length)throw new Error('Those versions already exist. Tell me what to change in them.');
      const result=await api('/api/ai/generate',{method:'POST',headers,body:JSON.stringify({brief:plan.action==='add_platforms'?(lastBrief||text):text,instruction:instagramInstruction(targets.includes('instagram')?'instagram':'',plan.action==='add_platforms'?text:''),platforms:targets,thread_length:+document.getElementById('threadLength').value,link_url:document.getElementById('linkUrl').value,draft_id:currentDraftId})});
      variants=result.variants;currentDraftId=result.draft_id;draftRevision=result.revision;lastBrief=plan.action==='add_platforms'?lastBrief:text;currentPlatform=targets[0];currentDraftStatus='draft';
      removeThinking();addAssistantMessage('Here’s a first draft. Tell me what you’d like to change.',draftWorkspace());
    }
    changeSerial++;await saveDraftNow();
  }catch(error){removeThinking();if(!Object.keys(variants).length)renderCanvas('<p>No new versions were created. Your message is retained in the conversation composer. Retry when you are ready.</p>');input.value=text;changeSerial++;addAssistantMessage(error.message||'Something went wrong. Your message is back in the composer.');setAutosaveStatus('Unsaved changes — retry');}
  finally{studioBusy(false);sizeComposer();if(window.matchMedia('(min-width: 761px)').matches)input.focus();}
}
async function loadRequestedDraft(){
  const id=new URLSearchParams(location.search).get('draft');
  try{
    if(!id)return;
    const row=await api(`/api/drafts/${encodeURIComponent(id)}`),ws=row.workspace||{};
    textHistory=ws.text_history||[];variants=row.variants||{};currentDraftId=row.id;draftRevision=row.revision||0;currentDraftStatus=row.status||'draft';lastBrief=row.brief||'';
    currentPlatform=ws.active_platform||row.platforms?.[0]||'x';if(Object.keys(variants).length&&!variants[currentPlatform])currentPlatform=Object.keys(variants)[0];
    uploadedMedia=ws.media||[];uploadedMediaIds=ws.media_asset_ids||[];uploadedMediaKind=ws.media_kind||null;uploadedVideoDuration=ws.video_duration||0;
    document.getElementById('brief').value=ws.composer||'';document.getElementById('linkUrl').value=ws.link_url||'';
    document.getElementById('threadLength').value=String(row.thread_length||1);
    document.getElementById('instagramFormat').value=ws.instagram_format||'post';
    const selected=ws.selected_platforms||row.platforms||[];document.querySelectorAll('.platform-check input').forEach(node=>node.checked=selected.includes(node.value));
    conversation=[];document.getElementById('chatFeed').innerHTML='';
    for(const message of ws.conversation||[]){if(message.role==='user')addUserMessage(message.content);else addAssistantMessage(message.content);}
    if(Object.keys(variants).length)renderCanvas(draftWorkspace());
    if(!conversation.length&&!Object.keys(variants).length)addAssistantMessage('Your saved workspace is ready.');
    renderAttachments();setAutosaveStatus(editableDraft()?'Saved':currentDraftStatus);
    if(currentDraftStatus!=='draft')await refreshPublicationResults();
  }catch(error){addAssistantMessage(error.message);currentDraftStatus='unavailable';document.getElementById('generateBtn').disabled=true;document.getElementById('brief').readOnly=true;return;}
  finally{studioLoading=false;studioBusy(false);sizeComposer();renderReadiness();renderRecentPosts();}
}
async function newConversation(){
  if(sendingMessage||studioLoading)return;
  try{await saveDraftNow();}catch(error){addAssistantMessage('Your changes could not be saved. Retry saving before starting a new chat.');return;}
  clearTimeout(autosaveTimer);invalidateReview();mediaUploadVersion++;mediaUploading=false;
  document.getElementById('instagramFormat').value='post';
  variants={};textHistory=[];publicationStates={};document.getElementById('undoStatus').textContent='';currentDraftId=null;draftRevision=0;currentDraftStatus='draft';conversation=[];lastBrief='';pendingSchedule=null;
  uploadedMedia=[];uploadedMediaIds=[];uploadedMediaKind=null;uploadedVideoDuration=0;changeSerial=0;savedSerial=0;
  history.replaceState({},'',window.zovaWorkspaceUrl('/studio'));document.getElementById('chatFeed').innerHTML='';
  document.getElementById('brief').value='';document.getElementById('linkUrl').value='';document.getElementById('mediaInput').value='';document.getElementById('mediaInput').disabled=false;
  editingDraft=false;renderRecentPosts();document.getElementById('postSettings').close();studioBusy(false);renderAttachments();addAssistantMessage('What would you like to create? Share an idea or attach your media.');setAutosaveStatus('Saved');sizeComposer();document.getElementById('brief').focus();
}
document.getElementById('mediaInput').addEventListener('change',async()=>{await uploadMedia();scheduleAutosave();});
document.getElementById('brief').addEventListener('keydown',event=>{if(event.key==='Enter'&&!event.shiftKey&&!event.isComposing&&(event.ctrlKey||event.metaKey||window.matchMedia('(min-width: 761px)').matches)){event.preventDefault();sendMessage();}});
document.getElementById('brief').addEventListener('input',scheduleAutosave);
document.getElementById('linkUrl').addEventListener('input',scheduleAutosave);
document.querySelectorAll('.platform-check input,#threadLength,#instagramFormat').forEach(node=>node.addEventListener('change',scheduleAutosave));
window.addEventListener('beforeunload',event=>{if(savedSerial!==changeSerial||mediaUploading||sendingMessage){event.preventDefault();event.returnValue='';}});
window.addEventListener('DOMContentLoaded',()=>{renderReadiness();loadRequestedDraft();});
