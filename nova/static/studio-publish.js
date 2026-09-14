/* Review stores a server-owned snapshot; final confirmation never re-reads editable text. */
let pendingReview=null;
let reviewPlatforms=[];
function mediaPreview(asset){return asset.url?(asset.kind==='video'?`<video controls preload="metadata" src="${esc(asset.url)}" aria-label="${esc(asset.filename)}"></video>`:`<img src="${esc(asset.url)}" alt="${esc(asset.filename)}">`):`<p>${esc(asset.filename)} — preview unavailable</p>`;}
async function requestPublishConfirmation(mode,scheduledLocal=null,targets=null){
  if(mediaUploading||!editableDraft())return addAssistantMessage('Finish the upload or check this draft’s current results first.');
  reviewPlatforms=targets||selectedPlatforms().filter(p=>variants[p]);
  if(!reviewPlatforms.length)return addAssistantMessage('Select at least one platform with a draft.');
  invalidateReview();reviewMode=mode;pendingSchedule=scheduledLocal;
  const epoch=reviewEpoch;
  try{
    await saveDraftNow();if(epoch!==reviewEpoch)return;
    const result=await api('/api/publish-context',{method:'POST',headers,body:JSON.stringify({platforms:reviewPlatforms,variants})});if(epoch!==reviewEpoch)return;reviewContexts=result.platforms;
    const blocked=reviewPlatforms.filter(p=>reviewContexts[p]?.error);
    if(blocked.length){
      const ready=reviewPlatforms.filter(p=>!blocked.includes(p));
      reviewHost().innerHTML=`<section class="chat-confirmation"><h3>Choose what to review now</h3><p>${blocked.map(platformName).join(', ')} need a connection or permission check. Their versions remain saved here.</p><a href="/account#socials">Manage connections</a>${ready.length?`<button class="button primary" onclick="requestPublishConfirmation('${mode}',null,${esc(JSON.stringify(ready))})">Review ${ready.map(platformName).join(', ')} only</button>`:''}</section>`;openReview();return;
    }
    const needsSettings=mode==='schedule'||reviewPlatforms.includes('tiktok')||reviewPlatforms.some(p=>(reviewContexts[p]?.accounts||[]).length>1);
    if(!needsSettings)return buildPublicationReview();
    let controls=reviewPlatforms.map(p=>`<label>${platformName(p)} destination<select data-destination="${p}">${(reviewContexts[p].accounts||[]).map(a=>`<option value="${a.id}" ${a.id===reviewContexts[p].connection_id?'selected':''}>${esc(a.name)} (${esc(a.account_id)})</option>`).join('')}</select></label>`).join('');
    if(reviewPlatforms.includes('tiktok')){
      const c=reviewContexts.tiktok;
      controls+=`<label>TikTok privacy<select id="reviewPrivacy" required><option value="">Choose privacy</option>${(c.privacy_options||[]).map(v=>`<option>${esc(v)}</option>`).join('')}</select></label>${[['allow_comment','Allow comments','comment_disabled'],['allow_duet','Allow Duet','duet_disabled'],['allow_stitch','Allow Stitch','stitch_disabled'],['your_brand','Promotes my own brand',''],['brand_content','Paid brand partnership','']].map(([key,label,disabled])=>`<label><input id="review_${key}" type="checkbox" ${c[disabled]?'disabled':''}> ${label}</label>`).join('')}`;
    }
    if(mode==='schedule')controls+=`<label>Posting time (your Zova account timezone)<input id="reviewTime" type="datetime-local" value="${esc(scheduledLocal||'')}" required></label><p>The final review will show the timezone and exact time.</p><button type="button" onclick="loadTimeSuggestions(this)">Suggest starting times</button><div id="timeSuggestions"></div>`;
    reviewHost().insertAdjacentHTML('beforeend',`<section class="chat-confirmation"><h3>Review destinations and settings</h3>${controls}<button class="button primary" onclick="buildPublicationReview()">Review final post</button></section>`);openReview();
  }catch(error){addAssistantMessage(error.message);}
}
async function buildPublicationReview(){
  const epoch=reviewEpoch,id=currentDraftId;
  const connection_ids={},options={};
  for(const p of reviewPlatforms)connection_ids[p]=Number(document.querySelector(`[data-destination="${p}"]`)?.value||reviewContexts[p].connection_id);
  if(reviewPlatforms.includes('tiktok')){
    const privacy=document.getElementById('reviewPrivacy')?.value;if(!privacy)return addAssistantMessage('Choose TikTok privacy before continuing.');
    options.tiktok={privacy_level:privacy,video_duration_sec:uploadedVideoDuration};
    ['allow_comment','allow_duet','allow_stitch','your_brand','brand_content'].forEach(key=>options.tiktok[key]=Boolean(document.getElementById('review_'+key)?.checked));
  }
  const body={draft_id:currentDraftId,platforms:[...reviewPlatforms],variants:Object.fromEntries(reviewPlatforms.map(p=>[p,variants[p]])),media_asset_ids:[...uploadedMediaIds],link_url:document.getElementById('linkUrl').value,publish_options:options,connection_ids};
  if(reviewMode==='schedule'){body.scheduled_local=document.getElementById('reviewTime')?.value||pendingSchedule;if(!body.scheduled_local)return addAssistantMessage('Choose a posting time.');}
  try{
    await saveDraftNow();const result=await api('/api/publish-review',{method:'POST',headers,body:JSON.stringify(body)});
    if(epoch!==reviewEpoch||id!==currentDraftId)return;
    pendingReview=result;document.querySelectorAll('.chat-confirmation').forEach(node=>node.remove());
    const s=result.snapshot;
    reviewHost().insertAdjacentHTML('beforeend',`<section class="chat-confirmation"><h3>${s.scheduled_utc?'Confirm schedule':'Confirm publish'}</h3>${s.platforms.map(p=>`<article><h4>${platformName(p)} · ${esc(s.targets[p].display_name)} ${s.targets[p].username?'@'+esc(s.targets[p].username):''}</h4><small>Account ${esc(s.targets[p].account_id)}</small>${s.targets[p].link?`<p>Attached link: ${esc(s.targets[p].link)}</p>`:''}${s.targets[p].posts.map(text=>`<p class="review-copy">${esc(text)}</p>`).join('')}${s.publish_options[p]?`<p>Privacy: ${esc(s.publish_options[p].privacy_level)} · Comments: ${s.publish_options[p].allow_comment?'on':'off'} · Duet: ${s.publish_options[p].allow_duet?'on':'off'} · Stitch: ${s.publish_options[p].allow_stitch?'on':'off'} · Own brand: ${s.publish_options[p].your_brand?'yes':'no'} · Partnership: ${s.publish_options[p].brand_content?'yes':'no'}</p>`:''}</article>`).join('')}<div class="review-media">${s.media.map(mediaPreview).join('')}</div>${s.link_url?`<p>Source link: ${esc(s.link_url)}</p>`:''}<p>${s.scheduled_utc?'Scheduled for '+esc(new Date(s.scheduled_utc).toLocaleString(undefined,{timeZone:s.timezone}))+' ('+esc(s.timezone)+')':'Publish these reviewed versions now?'}</p><button class="button ghost" onclick="invalidateReview();canvasView('edit')">Make a change</button><button class="button primary" onclick="confirmChatPublish(this)">${s.scheduled_utc?'Confirm schedule':'Confirm publish'}</button></section>`);openReview();
  }catch(error){addAssistantMessage(error.message);}
}
function showPublicationResults(result){
  publicationStates=Object.fromEntries(Object.entries(result.results||{}).map(([p,r])=>[p,r.status]));refreshDraft();
  document.querySelectorAll('[data-publication-results]').forEach(node=>node.remove());
  const entries=Object.entries(result.results||{});
  const remaining=Object.keys(variants).filter(p=>!Object.hasOwn(result.results||{},p));
  reviewHost().insertAdjacentHTML('beforeend',`<section data-publication-results class="chat-confirmation"><h3>Publication results</h3>${entries.map(([p,r])=>`<p><b>${platformName(p)}: ${esc(publicationStatus(r.status))}</b> ${r.requires_tiktok_completion?'Complete this video in TikTok; it is not published yet.':r.status==='pending'?'The platform is still processing this post.':''}${r.error?`<br>${esc(r.error)}`:''}${r.url&&/^https?:\/\//.test(r.url)?` <a target="_blank" rel="noopener" href="${esc(r.url)}">View post</a>`:''}${r.status==='failed'?` <button onclick="requestPublishConfirmation('publish',null,['${p}'])">Review and retry ${platformName(p)}</button>`:''}</p>`).join('')}${remaining.length?`<p>${remaining.map(platformName).join(', ')} were not submitted. Keep working on them in a separate idea.</p><button onclick="continueUnsubmitted(this,${esc(JSON.stringify(remaining))})">Continue unsubmitted versions</button>`:''}<button onclick="refreshPublicationResults()">Refresh results</button><a href="/drafts">Open drafts and schedules</a></section>`);openReview();
}
async function refreshPublicationResults(){const id=currentDraftId;try{const result=await api(`/api/publications/${id}`);if(id!==currentDraftId)return;currentDraftStatus=result.draft_status;refreshDraft();showPublicationResults(result);}catch(error){addAssistantMessage(error.message);}}
async function confirmChatPublish(button){
  if(!pendingReview||mediaUploading||sendingMessage)return;
  const review=JSON.parse(JSON.stringify(pendingReview)),s=review.snapshot;
  studioBusy(true);busy(button,true,s.scheduled_utc?'Scheduling…':'Publishing…');
  const body={review_token:review.review_token,draft_id:s.draft_id,platforms:s.platforms,variants:s.variants,media_asset_ids:s.media_asset_ids,link_url:s.link_url,publish_options:s.publish_options};
  if(s.scheduled_utc)body.scheduled_local=s.scheduled_utc;
  try{
    await saveDraftNow();const result=await api(s.scheduled_utc?'/api/schedule':'/api/publish',{method:'POST',headers,body:JSON.stringify(body)});
    currentDraftStatus=result.draft_status;invalidateReview();refreshDraft();showPublicationResults(result);
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
    studioBusy(false);location.href=`/studio?draft=${row.id}`;
  }catch(error){addAssistantMessage('Could not copy the unsubmitted versions. They are still retained here. '+error.message);button.disabled=false;}
  finally{studioBusy(false);}
}
