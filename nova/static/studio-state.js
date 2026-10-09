/* Persistence and conversation lifecycle. The editor/sidebar remain in studio.js. */
let draftRevision = 0;
let plannedOccurrence = null;
let changeSerial = 0;
let savedSerial = 0;
let sendingMessage = false;
let studioLoading = true;
let saveLabel = 'Ready';
let workspaceEpoch=0;
let retryTurn=null;
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
      conversation,text_history:textHistory,composer:document.getElementById('brief').value,selected_platforms:selectedPlatforms(),platform_selection_explicit:platformSelectionExplicit,active_platform:currentPlatform}};
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
function promptComposer(text){if(sendingMessage||studioLoading)return;studioView('chat');const input=document.getElementById('brief');input.value=text;input.focus();input.setSelectionRange(text.length,text.length);sizeComposer();scheduleAutosave();}
function studioBusy(active){
  sendingMessage=active;
  document.getElementById('generateBtn').disabled=active||!editableDraft()||!document.getElementById('brief').value.trim();
  document.getElementById('brief').readOnly=active||!editableDraft();
  document.getElementById('newChatBtn').disabled=active;
  document.querySelectorAll('#variantEditor textarea').forEach(node=>node.readOnly=active||!editableDraft());
  document.querySelectorAll('.platform-check input,[name=instagramFormatChoice],#threadLength,#instagramFormat,#linkUrl,#mediaInput,.attachment-details button').forEach(node=>node.disabled=active||!editableDraft());
}
async function sendMessage(){
  const input=document.getElementById('brief'),text=input.value.trim();
  if(!text||sendingMessage||studioLoading||mediaUploading||!editableDraft())return;
  studioBusy(true);invalidateReview();
  const epoch=workspaceEpoch;let responseApplied=false,turnAdded=false;
  try{
    await saveDraftNow();
    if(epoch!==workspaceEpoch)return;
    addThinking();
    const plan=await api('/api/conversation/plan',{method:'POST',headers,body:JSON.stringify({message:text,draft_id:currentDraftId,selected_platforms:selectedPlatforms(),platform_selection_explicit:platformSelectionExplicit,active_platform:currentPlatform,recent_messages:conversation.slice(-12),media_asset_ids:uploadedMediaIds})});
    if(epoch!==workspaceEpoch)return;
    removeThinking();stickToLatest=true;
    if(!(retryTurn?.draftId===currentDraftId&&retryTurn.text===text))addUserMessage(text);
    turnAdded=true;retryTurn=null;
    if(plan.media_inspection?.length)showMediaInspection(plan.media_inspection);scrollChat(true);input.value='';sizeComposer();changeSerial++;addThinking();
    if(plan.action==='answer'){removeThinking();addAssistantMessage(plan.reply||'What would you like to create or change?');}
    else if(plan.action==='insight'){
      const result=await api('/api/insights',{method:'POST',headers,body:JSON.stringify({question:text})});if(epoch!==workspaceEpoch)return;removeThinking();addAssistantMessage(result.answer);
    }else if(plan.action==='publish'||plan.action==='schedule'){
      removeThinking();await saveDraftNow();
      if(!Object.keys(variants).length)addAssistantMessage('Create a draft first, then review it before publishing.');
      else if(plan.action==='publish')await requestPublishConfirmation('publish');else await suggestSchedule(text);
    }else if(plan.action==='rewrite'){
      const targets=plan.platforms.length?plan.platforms:[currentPlatform],changed={};
      for(const p of targets){
        if(!variants[p])throw new Error(`Add a ${platformName(p)} version first.`);
        const result=await api('/api/ai/rewrite',{method:'POST',headers,body:JSON.stringify({media_asset_ids:uploadedMediaIds,platform:p,posts:variants[p].posts,action:'',instruction:instagramInstruction(p,plan.brief||text)})});
        if(epoch!==workspaceEpoch)return;
        changed[p]={posts:result.posts};
      }
      rememberTextRevision();Object.assign(variants,changed);currentPlatform=targets[0];removeThinking();addAssistantMessage(`Here’s the revised ${targets.map(platformName).join(' and ')} ${targets.length===1?'version':'copy'}.`,draftWorkspace());
    }else{
      const platforms=plan.platforms.length?plan.platforms:selectedPlatforms();
      const creationBrief=plan.brief||[lastBrief,...conversation.filter(m=>m.role==='user').slice(-4).map(m=>m.content)].filter(Boolean).join('\n').slice(-12000);
      if(!platforms.length)throw new Error('Choose at least one platform.');
      if(!validateVideoPlatforms(platforms))throw new Error('Videos can only be used with Instagram and TikTok.');
      const newDraft=plan.action==='create' && Object.keys(variants).length>0;
      if(newDraft)await saveDraftNow();
      const targets=plan.action==='add_platforms'?platforms.filter(p=>!variants[p]):platforms;
      if(!targets.length)throw new Error('Those versions already exist. Tell me what to change in them.');
      const result=await api('/api/ai/generate',{method:'POST',headers,body:JSON.stringify({media_asset_ids:uploadedMediaIds,brief:plan.action==='add_platforms'?(lastBrief||text):creationBrief,instruction:instagramInstruction(targets.includes('instagram')?'instagram':'',plan.action==='add_platforms'?text:''),platforms:targets,thread_length:+document.getElementById('threadLength').value,link_url:document.getElementById('linkUrl').value,draft_id:newDraft?null:currentDraftId})});
      if(epoch!==workspaceEpoch)return;
      if(newDraft){textHistory=[];publicationStates={};currentDraftTitle='';}
      selectStudioPlatforms(plan.action==='add_platforms'?[...new Set([...selectedPlatforms(),...targets])]:targets);
      history.replaceState({},'',window.zovaWorkspaceUrl(`/studio?draft=${result.draft_id}`));
      variants=result.variants;currentDraftId=result.draft_id;draftRevision=result.revision;lastBrief=plan.action==='add_platforms'?lastBrief:creationBrief;currentPlatform=targets[0];currentDraftStatus='draft';
      currentDraftTitle=result.display_title||result.title||currentDraftTitle;
      removeThinking();addAssistantMessage(plan.action==='add_platforms'?`I’ve added ${targets.map(platformName).join(' and ')}. Your other versions are still here.`:'Here’s a first draft. What would make it sound more like you?',draftWorkspace());
    }
    if(epoch!==workspaceEpoch)return;
    responseApplied=true;changeSerial++;await saveDraftNow();
  }catch(error){
    if(epoch!==workspaceEpoch)return;
    removeThinking();
    if(responseApplied){setAutosaveStatus('Save failed — retry');document.getElementById('undoStatus').textContent='Your response is ready here, but it has not saved. Use Retry save to keep it.';}
    else{input.value=text;retryTurn=turnAdded?{draftId:currentDraftId,text}:null;changeSerial++;addAssistantMessage(error.message||'I couldn’t finish that yet. Your message is ready to try again.');try{await saveDraftNow();}catch{setAutosaveStatus('Unsaved changes — retry');}}
  }
  finally{if(epoch===workspaceEpoch){studioBusy(false);renderReadiness();sizeComposer();if(window.matchMedia('(min-width: 761px)').matches)input.focus();}}
}
async function loadRequestedDraft(){
  const epoch=++workspaceEpoch;
  const id=new URLSearchParams(location.search).get('draft');
  try{
    if(!id)return;
    const row=await api(`/api/drafts/${encodeURIComponent(id)}`),ws=row.workspace||{};
    if(epoch!==workspaceEpoch)return;
    currentDraftTitle=row.display_title||row.title||'';platformSelectionExplicit=row.workspace?.platform_selection_explicit===true;retryTurn=null;
    plannedOccurrence=row.planned||null;
    textHistory=ws.text_history||[];variants=row.variants||{};currentDraftId=row.id;draftRevision=row.revision||0;currentDraftStatus=row.status||'draft';lastBrief=row.brief||'';
    currentPlatform=ws.active_platform||row.platforms?.[0]||'x';if(Object.keys(variants).length&&!variants[currentPlatform])currentPlatform=Object.keys(variants)[0];
    uploadedMedia=ws.media||[];uploadedMediaIds=ws.media_asset_ids||[];uploadedMediaKind=ws.media_kind||null;uploadedVideoDuration=ws.video_duration||0;
    document.getElementById('brief').value=ws.composer||'';document.getElementById('linkUrl').value=ws.link_url||'';
    document.getElementById('threadLength').value=String(row.thread_length||1);
    document.getElementById('instagramFormat').value=ws.instagram_format||'post';
    const selected=savedPlatformSelection(row);document.querySelectorAll('.platform-check input').forEach(node=>node.checked=selected.includes(node.value));
    conversation=[];document.getElementById('chatFeed').innerHTML='';
    for(const message of ws.conversation||[]){if(message.role==='user')addUserMessage(message.content);else addAssistantMessage(message.content);}
    if(Object.keys(variants).length)renderCanvas(draftWorkspace());
    if(!conversation.length&&!Object.keys(variants).length)addAssistantMessage('Your saved workspace is ready.');
    renderAttachments();setAutosaveStatus(editableDraft()?'Saved':currentDraftStatus);
    if(currentDraftStatus!=='draft')await refreshPublicationResults();
  }catch(error){if(epoch!==workspaceEpoch)return;addAssistantMessage(error.message);currentDraftStatus='unavailable';document.getElementById('generateBtn').disabled=true;document.getElementById('brief').readOnly=true;return;}
  finally{if(epoch===workspaceEpoch){studioLoading=false;studioBusy(false);sizeComposer();renderReadiness();renderRecentPosts();}}
}
async function newConversation(){
  if(sendingMessage||studioLoading)return;
  try{await saveDraftNow();}catch(error){addAssistantMessage('Your changes could not be saved. Retry saving before starting a new chat.');return;}
  workspaceEpoch++;retryTurn=null;currentDraftTitle='';
  clearTimeout(autosaveTimer);invalidateReview();mediaUploadVersion++;mediaUploading=false;
  document.getElementById('instagramFormat').value='post';
  plannedOccurrence=null;variants={};textHistory=[];publicationStates={};document.getElementById('undoStatus').textContent='';currentDraftId=null;draftRevision=0;currentDraftStatus='draft';conversation=[];lastBrief='';pendingSchedule=null;
  uploadedMedia=[];uploadedMediaIds=[];uploadedMediaKind=null;uploadedVideoDuration=0;changeSerial=0;savedSerial=0;
  history.replaceState({},'',window.zovaWorkspaceUrl('/studio'));document.getElementById('chatFeed').innerHTML='';
  document.getElementById('brief').value='';document.getElementById('linkUrl').value='';document.getElementById('mediaInput').value='';document.getElementById('mediaInput').disabled=false;
  editingDraft=false;renderReadiness();renderRecentPosts();document.getElementById('postSettings').close();studioBusy(false);renderAttachments();addAssistantMessage('How can we grow your engagement today? Share your ideas. Zova’s AI helps shape them into a plan and posts in your voice.');setAutosaveStatus('Ready');sizeComposer();document.getElementById('brief').focus();
}
document.getElementById('mediaInput').addEventListener('change',async()=>{await uploadMedia();scheduleAutosave();});
document.getElementById('brief').addEventListener('keydown',event=>{if(event.key==='Enter'&&!event.shiftKey&&!event.isComposing&&(event.ctrlKey||event.metaKey||window.matchMedia('(min-width: 761px)').matches)){event.preventDefault();sendMessage();}});
document.getElementById('brief').addEventListener('input',scheduleAutosave);
document.getElementById('linkUrl').addEventListener('input',scheduleAutosave);
document.querySelectorAll('.platform-check input,#threadLength,#instagramFormat').forEach(node=>node.addEventListener('change',()=>{if(node.matches('.platform-check input'))platformSelectionExplicit=true;scheduleAutosave();}));
window.addEventListener('beforeunload',event=>{if(savedSerial!==changeSerial||mediaUploading||sendingMessage){event.preventDefault();event.returnValue='';}});
window.addEventListener('DOMContentLoaded',()=>{renderReadiness();loadRequestedDraft();});

async function switchStudioBrand(event){
 event.preventDefault();
 const status=document.getElementById('brandSwitchStatus');
 if(sendingMessage||mediaUploading){status.textContent='Wait for your current request to finish before switching.';return;}
 const form=event.target;
 try{await saveDraftNow();form.submit();}
 catch{status.textContent='Your changes have not saved. Retry saving before switching workspaces.';}
}
