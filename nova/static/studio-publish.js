
function tiktokDeclaration(paid){return `<p>By posting, you agree to TikTok’s ${paid?'<a href="https://www.tiktok.com/legal/page/global/bc-policy/en" target="_blank" rel="noopener">Branded Content Policy</a> and ':''}<a href="https://www.tiktok.com/legal/page/global/music-usage-confirmation/en" target="_blank" rel="noopener">Music Usage Confirmation</a>.</p>`;}
let tiktokPrivateTestMode=false;
function tiktokDirectControls(c){
 tiktokPrivateTestMode=c.private_test_mode===true;
 const video=uploadedMediaKind==='video';
 const interactions=[['allow_comment','Allow comments','comment_disabled'],...(video?[['allow_duet','Allow Duet','duet_disabled'],['allow_stitch','Allow Stitch','stitch_disabled']]:[])];
 return `<div id="tiktokDirectSettings"><p>Posting to ${esc(c.display_name)}${c.username?' @'+esc(c.username):''}</p><label>Who can see this post?<select id="reviewPrivacy" onchange="resetTikTokConsent();updateTikTokControls()" required><option value="">Choose privacy</option>${(c.privacy_options||[]).map(v=>`<option value="${esc(v)}">${esc(({PUBLIC_TO_EVERYONE:'Everyone',MUTUAL_FOLLOW_FRIENDS:'Friends',FOLLOWER_OF_CREATOR:'Followers',SELF_ONLY:'Only me'})[v]||v)}</option>`).join('')}</select></label>${interactions.map(([key,label,disabled])=>`<label><input id="review_${key}" type="checkbox" ${c[disabled]?'disabled':''}> ${label}${c[disabled]?' (unavailable for this account)':''}</label>`).join('')}<label><input id="review_is_aigc" type="checkbox"> This media is AI-generated</label><label><input id="review_commercial_content" type="checkbox" onchange="resetTikTokConsent();updateTikTokControls()"> This post promotes a brand, product or service</label><div id="tiktokDisclosure" hidden><label><input id="review_your_brand" type="checkbox" onchange="resetTikTokConsent();updateTikTokControls()"> Your brand</label><label><input id="review_brand_content" type="checkbox" onchange="resetTikTokConsent();updateTikTokControls()"> Branded content (paid partnership)</label><p id="tiktokDisclosureLabel" aria-live="polite"></p></div><p id="tiktokPrivacyNote" aria-live="polite"></p><div id="tiktokDeclaration">${tiktokDeclaration(false)}</div><label><input id="review_consent" type="checkbox" onchange="updateTikTokControls()"> I agree and want to post this content to TikTok</label><p>${video?'Video duration is checked against your account limit. ':''}You can edit the caption and preview your media before final confirmation.</p></div>`;
}
function resetTikTokConsent(){const n=document.getElementById('review_consent');if(n)n.checked=false;}
function updateTikTokControls(){
 const node=id=>document.getElementById(id),commercial=node('review_commercial_content')?.checked||false;
 const own=node('review_your_brand'),paid=node('review_brand_content'),privacy=node('reviewPrivacy');
 if(!privacy)return true;
 if(!commercial){own.checked=false;paid.checked=false;}
 node('tiktokDisclosure').hidden=!commercial;
 const privatePost=privacy.value==='SELF_ONLY';
 const paidPrivacyUnavailable=privatePost||privacy.value==='FOLLOWER_OF_CREATOR';
 if(paidPrivacyUnavailable)paid.checked=false;
 paid.disabled=paidPrivacyUnavailable;
 for(const option of privacy.options||[])option.disabled=!!option.value&&((tiktokPrivateTestMode&&option.value!=='SELF_ONLY')||(paid.checked&&!['PUBLIC_TO_EVERYONE','MUTUAL_FOLLOW_FRIENDS'].includes(option.value)));
 node('tiktokPrivacyNote').textContent=tiktokPrivateTestMode?'TikTok testing requires a private account and Only me visibility. Paid partnerships need TikTok approval.':paidPrivacyUnavailable?'Branded content cannot use Only me or Followers privacy. Choose Everyone or Friends.':'';
 node('tiktokDisclosureLabel').textContent=paid.checked?'Your post will be labelled Paid partnership.':own.checked?'Your post will be labelled Promotional content.':'Choose Your brand, Branded content, or both.';
 node('tiktokDeclaration').innerHTML=tiktokDeclaration(paid.checked);
 const ready=!!privacy.value&&(!commercial||own.checked||paid.checked)&&!!node('review_consent')?.checked&&(!tiktokPrivateTestMode||(privatePost&&!paid.checked));
 const button=document.getElementById('reviewFinalPost');if(button){button.disabled=!ready;button.title=commercial&&!own.checked&&!paid.checked?'Choose what your content promotes.':'';}
 return ready;
}
async function changeReviewDestination(){
 const ids={};for(const p of reviewPlatforms)ids[p]=Number(document.querySelector(`[data-destination="${p}"]`)?.value||reviewContexts[p].connection_id);
 await requestPublishConfirmation(reviewMode,pendingSchedule,[...reviewPlatforms],ids);
}

/* Review stores a server-owned snapshot; final confirmation never re-reads editable text. */
let pendingReview=null;
let reviewPlatforms=[];
function mediaPreview(asset){return asset.url?(asset.kind==='video'?`<video controls preload="metadata" src="${esc(mediaPreviewUrl(asset.url))}" aria-label="${esc(asset.filename)}"></video>`:`<img src="${esc(mediaPreviewUrl(asset.url))}" alt="${esc(asset.filename)}">`):`<p>${esc(asset.filename)} — preview unavailable</p>`;}
async function requestPublishConfirmation(mode,scheduledLocal=null,targets=null,connectionIds={}){
  if(mediaUploading||!editableDraft())return addAssistantMessage('Finish the upload or check this draft’s current results first.');
  reviewPlatforms=targets||selectedPlatforms().filter(p=>variants[p]);
  if(!reviewPlatforms.length)return addAssistantMessage('Select at least one platform with a draft.');
  scheduledLocal=scheduledLocal||(mode==='schedule'?plannedOccurrence?.local_time:null);
  invalidateReview();reviewMode=mode;pendingSchedule=scheduledLocal;
  const epoch=reviewEpoch;
  try{
    await saveDraftNow();if(epoch!==reviewEpoch)return;
    const result=await api('/api/publish-context',{method:'POST',headers,body:JSON.stringify({platforms:reviewPlatforms,variants,connection_ids:connectionIds})});if(epoch!==reviewEpoch)return;reviewContexts=result.platforms;
    const blocked=reviewPlatforms.filter(p=>reviewContexts[p]?.error);
    if(blocked.length){
      const ready=reviewPlatforms.filter(p=>!blocked.includes(p));
      reviewHost().innerHTML=`<section class="chat-confirmation"><h3>Choose what to review now</h3><p>${blocked.map(platformName).join(', ')} need a connection or permission check. Their versions remain saved here.</p><a href="/account#socials">Manage connections</a>${ready.length?`<button class="button primary" onclick="requestPublishConfirmation('${mode}',null,${esc(JSON.stringify(ready))})">Review ${ready.map(platformName).join(', ')} only</button>`:''}</section>`;openReview();return;
    }
    const needsSettings=mode==='schedule'||reviewPlatforms.includes('tiktok')||reviewPlatforms.some(p=>(reviewContexts[p]?.accounts||[]).length>1);
    if(!needsSettings)return buildPublicationReview();
    let controls=reviewPlatforms.map(p=>`<label>${window.zovaPlatformLabel(p)} destination<select data-destination="${p}" onchange="changeReviewDestination()">${(reviewContexts[p].accounts||[]).map(a=>`<option value="${a.id}" ${a.id===reviewContexts[p].connection_id?'selected':''}>${esc(a.name)}</option>`).join('')}</select></label>`).join('');
    if(reviewPlatforms.includes('tiktok')){
      const c=reviewContexts.tiktok;
      if(c.posting_mode==='inbox')controls+=`<p>Send this video to your TikTok inbox. Finish the caption, privacy and publishing in TikTok. Zova does not publish it automatically.</p>`;
      else controls+=tiktokDirectControls(c);
    }
    if(mode==='schedule')controls+=`<label>Posting time (${esc(plannedOccurrence?.timezone||'your Zova account timezone')})<input id="reviewTime" type="datetime-local" value="${esc(scheduledLocal||'')}" required></label><p>The final review will show the timezone and exact time.</p><button type="button" onclick="loadTimeSuggestions(this)">Suggest starting times</button><div id="timeSuggestions"></div>`;
    reviewHost().insertAdjacentHTML('beforeend',`<section class="chat-confirmation"><h3>Review destinations and settings</h3>${controls}<button id="reviewFinalPost" class="button primary" onclick="buildPublicationReview()">Review final post</button></section>`);updateTikTokControls();openReview();
  }catch(error){if(epoch===reviewEpoch)addAssistantMessage(error.message);}
}
async function buildPublicationReview(){
  const epoch=reviewEpoch,id=currentDraftId;
  const connection_ids={},options={};
  if(reviewPlatforms.includes('instagram'))options.instagram={format:instagramFormat()};
  for(const p of reviewPlatforms)connection_ids[p]=Number(document.querySelector(`[data-destination="${p}"]`)?.value||reviewContexts[p].connection_id);
  if(reviewPlatforms.includes('instagram')){
    try{const audio=window.zovaInstagramMusic?.optionFor(connection_ids.instagram);if(audio)options.instagram.audio=audio;}
    catch(error){return addAssistantMessage(error.message);}
  }
  if(reviewPlatforms.includes('tiktok')){
    const inbox=reviewContexts.tiktok.posting_mode==='inbox';
    const privacy=document.getElementById('reviewPrivacy')?.value;if(!inbox&&!privacy)return addAssistantMessage('Choose TikTok privacy before continuing.');
    options.tiktok=inbox?{posting_mode:"inbox"}:{posting_mode:"direct",privacy_level:privacy,video_duration_sec:uploadedVideoDuration};
    if(!inbox&&!updateTikTokControls())return addAssistantMessage('Complete the TikTok settings and consent first.');
    if(!inbox)['allow_comment','allow_duet','allow_stitch','commercial_content','your_brand','brand_content','consent','is_aigc'].forEach(key=>options.tiktok[key]=Boolean(document.getElementById('review_'+key)?.checked));
  }
  const body={draft_id:currentDraftId,platforms:[...reviewPlatforms],variants:Object.fromEntries(reviewPlatforms.map(p=>[p,variants[p]])),media_asset_ids:[...uploadedMediaIds],link_url:document.getElementById('linkUrl').value,publish_options:options,connection_ids};
  if(reviewMode==='schedule'){body.scheduled_local=document.getElementById('reviewTime')?.value||pendingSchedule;if(!body.scheduled_local)return addAssistantMessage('Choose a posting time.');}
  try{
    await saveDraftNow();const result=await api('/api/publish-review',{method:'POST',headers,body:JSON.stringify(body)});
    if(epoch!==reviewEpoch||id!==currentDraftId)return;
    pendingReview=result;document.querySelectorAll('.chat-confirmation').forEach(node=>node.remove());
    const s=result.snapshot;
    const inboxOnly=s.platforms.length===1&&s.targets.tiktok?.requires_tiktok_completion;
    const confirmLabel=s.scheduled_utc?"Confirm schedule":inboxOnly?"Send to TikTok":"Confirm publish";
    reviewHost().insertAdjacentHTML('beforeend',`<section class="chat-confirmation"><h3>${confirmLabel}</h3>${s.platforms.map(p=>`<article><h4>${window.zovaPlatformLabel(p)}${p==='instagram'?' · '+esc(s.targets[p].format_label):''} · ${esc(s.targets[p].display_name)} ${s.targets[p].username?'@'+esc(s.targets[p].username):''}</h4>${s.targets[p].link?`<p>Attached link: ${esc(s.targets[p].link)}</p>`:''}${s.targets[p].format==='story'?'<p>Only the visual below will publish to your Story for 24 hours. Planning text and the source link are not included. No text overlays, stickers or music are added.</p>':''}${p==='instagram'&&s.publish_options.instagram?.audio?`<p>Music: ${esc(s.publish_options.instagram.audio.title)} · ${esc(s.publish_options.instagram.audio.artist)}. Music volume ${s.publish_options.instagram.audio.audio_volume}%; original audio ${s.publish_options.instagram.audio.video_volume}%. The combined audio cannot be previewed before publishing.</p>`:''}${s.targets[p].posts.map(text=>`<p class="review-copy">${esc(text)}</p>`).join('')}${s.targets[p].requires_tiktok_completion?'<p>Send video to TikTok inbox only. Caption, privacy and the final publish are completed in TikTok; text above is a reference and is not attached to the upload.</p>':''}${p==='tiktok'&&!s.targets[p].requires_tiktok_completion&&s.publish_options[p]?`<p>Privacy: ${esc(({SELF_ONLY:'Only me',PUBLIC_TO_EVERYONE:'Everyone',MUTUAL_FOLLOW_FRIENDS:'Friends',FOLLOWER_OF_CREATOR:'Followers'})[s.publish_options[p].privacy_level]||s.publish_options[p].privacy_level)} · Comments: ${s.publish_options[p].allow_comment?'on':'off'} · Duet: ${s.publish_options[p].allow_duet?'on':'off'} · Stitch: ${s.publish_options[p].allow_stitch?'on':'off'} · Own brand: ${s.publish_options[p].your_brand?'yes':'no'} · Partnership: ${s.publish_options[p].brand_content?'yes':'no'} · AI-generated media: ${s.publish_options[p].is_aigc?'yes':'no'}</p>${tiktokDeclaration(s.publish_options[p].brand_content)}<p>After confirmation, TikTok may take a few minutes to process your post before it appears on your profile.</p>`:''}</article>`).join('')}<div class="review-media">${s.media.map(mediaPreview).join('')}</div>${s.link_url?`<p>Source link: ${esc(s.link_url)}</p>`:''}<p>${s.scheduled_utc?'Scheduled for '+esc(new Date(s.scheduled_utc).toLocaleString(undefined,{timeZone:s.timezone}))+' ('+esc(s.timezone)+')':inboxOnly?'Send this reviewed video to your TikTok inbox now?':'Publish these reviewed versions now?'}</p><button class="button ghost" onclick="invalidateReview();canvasView('edit')">Edit caption / media</button><button class="button primary" onclick="confirmChatPublish(this)">${confirmLabel}</button></section>`);openReview();
  }catch(error){if(epoch===reviewEpoch)addAssistantMessage(error.message);}
}
function publicationSignature(result){return JSON.stringify(Object.entries(result.results||{}).map(([p,r])=>[p,r.status,r.url,r.delivered_to_inbox,r.requires_tiktok_completion,r.error]));}
let lastPublicationSignature='';
function showPublicationResults(result,automatic=false){
  lastPublicationSignature=publicationSignature(result);
  schedulePublicationRefresh(result);
  publicationStates=Object.fromEntries(Object.entries(result.results||{}).map(([p,r])=>[p,r.status]));refreshDraft();
  document.querySelectorAll('[data-publication-results]').forEach(node=>node.remove());
  const entries=Object.entries(result.results||{});
  const remaining=Object.keys(variants).filter(p=>!Object.hasOwn(result.results||{},p));
  reviewHost().insertAdjacentHTML('beforeend',`<section data-publication-results aria-live="polite" class="chat-confirmation"><h3>Publication results</h3>${entries.map(([p,r])=>`<p><b>${window.zovaPlatformLabel(p)}${r.format==='story'?' Story':''}: ${esc(r.status==='pending'&&r.delivered_to_inbox?'Delivered to TikTok inbox':publicationStatus(r.status))}</b> ${r.requires_tiktok_completion?'Complete this video in TikTok; it is not published yet.':r.status==='pending'?'The platform is processing your post. Zova checks automatically; you can leave this page.':''}${p==='tiktok'&&r.status==='published'&&!r.url?`<br>${r.privacy_level==='PUBLIC_TO_EVERYONE'?'Published. TikTok has not returned a public link yet.':'Published with restricted visibility. TikTok does not provide a public link for this post.'}`:''}${r.error?`<br>${esc(r.error)}`:''}${r.support_reference?`<br><small>Support reference: ${esc(r.support_reference)}</small>`:''}${r.url&&/^https?:\/\//.test(r.url)?` <a target="_blank" rel="noopener" href="${esc(r.url)}">${p==='tiktok'?'View on TikTok':'View post'}</a>`:''}${r.status==='failed'?` <button onclick="requestPublishConfirmation('publish',null,['${p}'])">Review and retry ${window.zovaPlatformLabel(p)}</button>`:''}</p>`).join('')}${remaining.length?`<p>${remaining.map(platformName).join(', ')} were not submitted. Keep working on them in a separate idea.</p><button onclick="continueUnsubmitted(this,${esc(JSON.stringify(remaining))})">Continue unsubmitted versions</button>`:''}<p id="publicationCheckNote" class="support-note"></p><button onclick="refreshPublicationResults()">Refresh results</button><a href="/drafts">Open Schedule</a></section>`);if(!automatic)openReview();
}
let publicationTimer=null,publicationPollKey='',publicationPollCount=0,publicationRefreshBusy=false;
function schedulePublicationRefresh(result){
 clearTimeout(publicationTimer);
 const key=currentDraftId+':'+workspaceEpoch;
 if(key!==publicationPollKey){publicationPollKey=key;publicationPollCount=0;}
 const pending=Object.entries(result.results||{}).some(([p,r])=>['pending','publishing','queued'].includes(r.status)&&!r.delivered_to_inbox||p==='tiktok'&&r.status==='published'&&!r.url&&r.privacy_level==='PUBLIC_TO_EVERYONE');
 if(!pending||publicationPollCount>=40)return;
 publicationTimer=setTimeout(()=>{if(key!==currentDraftId+':'+workspaceEpoch)return;publicationPollCount++;refreshPublicationResults(true);},15000);
}
async function refreshPublicationResults(automatic=false){const id=currentDraftId,epoch=workspaceEpoch;if(!id||publicationRefreshBusy)return;publicationRefreshBusy=true;try{const result=await api(`/api/publications/${id}`);if(id!==currentDraftId||epoch!==workspaceEpoch)return;currentDraftStatus=result.draft_status;if(!automatic||lastPublicationSignature!==publicationSignature(result)){showPublicationResults(result,automatic);rememberSavedPost();}else schedulePublicationRefresh(result);const note=document.getElementById('publicationCheckNote');if(note)note.textContent=publicationPollCount>=40?'Automatic checks paused. Refresh results for the latest status.':'Last checked '+new Date().toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'});}catch(error){if(id===currentDraftId&&epoch===workspaceEpoch){if(!automatic)addAssistantMessage(error.message);else{const note=document.getElementById('publicationCheckNote');if(note)note.textContent='Could not check the latest status. Use Refresh results to try again.';}}}finally{publicationRefreshBusy=false;}}

async function confirmChatPublish(button){
  if(!pendingReview||mediaUploading||sendingMessage)return;
  const review=JSON.parse(JSON.stringify(pendingReview)),s=review.snapshot;
  studioBusy(true);busy(button,true,s.scheduled_utc?'Scheduling…':s.platforms.length===1&&s.targets.tiktok?.requires_tiktok_completion?'Sending to TikTok…':'Publishing…');
  const body={review_token:review.review_token,draft_id:s.draft_id,platforms:s.platforms,variants:s.variants,media_asset_ids:s.media_asset_ids,link_url:s.link_url,publish_options:s.publish_options};
  if(s.scheduled_utc)body.scheduled_local=s.scheduled_utc;
  try{
    await saveDraftNow();const result=await api(s.scheduled_utc?'/api/schedule':'/api/publish',{method:'POST',headers,body:JSON.stringify(body)});
    currentDraftStatus=result.draft_status;invalidateReview();refreshDraft();showPublicationResults(result);rememberSavedPost();
  }catch(error){addAssistantMessage(error.message);}
  finally{studioBusy(false);busy(button,false);}
}
async function suggestSchedule(){await requestPublishConfirmation('schedule');}

let suggestedTimes=[];
async function loadTimeSuggestions(button){
 const id=currentDraftId;button.disabled=true;
 try{const data=await api('/api/ai/schedule',{method:'POST',headers,body:JSON.stringify({platforms:reviewPlatforms,context:lastBrief})});
 if(id!==currentDraftId||!document.getElementById('timeSuggestions'))return;
 suggestedTimes=Object.entries(data.suggestions||{}).flatMap(([platform,items])=>Array.isArray(items)?items.map(item=>({...item,platform})):[]);
 document.getElementById('timeSuggestions').innerHTML=`<p>${esc(data.note)} Times use ${esc(data.timezone)}. The chosen time applies to the selected platforms.</p>`+suggestedTimes.map((item,index)=>`<button type="button" onclick="document.getElementById('reviewTime').value=suggestedTimes[${index}].local_time">${esc(platformName(item.platform))}: ${esc(item.label)} ${esc(item.local_time)}</button>`).join('');
 }catch(error){if(id===currentDraftId)addAssistantMessage(error.message);}finally{button.disabled=false;}
}

async function continueUnsubmitted(button,platforms){
  if(sendingMessage||!platforms.length)return;
  studioBusy(true);button.disabled=true;
  try{
    const payload=draftPayload();payload.platforms=platforms;
    payload.variants=Object.fromEntries(platforms.map(p=>[p,variants[p]]));
    payload.workspace.selected_platforms=platforms;payload.workspace.active_platform=platforms[0];payload.workspace.text_history=[];
    const row=await api('/api/drafts',{method:'POST',headers,body:'{}'});payload.revision=row.revision;
    await api(`/api/drafts/${row.id}`,{method:'PATCH',headers,body:JSON.stringify(payload)});
    studioBusy(false);location.href=window.zovaWorkspaceUrl(`/studio?draft=${row.id}`);
  }catch(error){addAssistantMessage('Could not copy the unsubmitted versions. They are still retained here. '+error.message);button.disabled=false;}
  finally{studioBusy(false);}
}
