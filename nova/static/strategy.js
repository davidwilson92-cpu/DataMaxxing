/* Strategy is saved per brand; Next move is a separate, immediate action. */
let hasConfirmedStrategy=false;
let moveItems=[],moveIndex=0,moveOffset=0;
const moveRefinements=new Map();
let strategyData={},strategyInputSnapshot="";
const movePlatform=p=>window.zovaPlatformLabel?window.zovaPlatformLabel(p):esc(platformName(p));
let strategyRevision=0,strategyLoaded=false,strategyPending=false,seriesRequestKey=null,seriesPreviewBody=null;
let strategyViewEpoch=0,strategyOperation=0,strategyPlanning=false,strategyDescription='',quickMoveRequest=null;
const strategyStatus=text=>{document.getElementById('strategyStatus').textContent=text;};
function strategySnapshot(){return {...strategyData};}
function conciseCopy(text,limit=32){
 const clean=String(text||'').replace(/\s+/g,' ').trim(),words=clean.split(' ');
 return words.length>limit?words.slice(0,limit).join(' ').replace(/[,;:]$/,'')+'…':clean;
}
function strategyInputs(){return {brief:document.getElementById('strategyBrief').value.trim(),content_direction:document.getElementById('strategyDirection').value.trim()};}
function strategySummary(){
 const data=strategyData,rows=[['Aim',data.goal],['Post about',data.themes],['Pace',data.rhythm]];
 document.getElementById('strategySummary').innerHTML=rows.filter(([,value])=>value).map(([label,value])=>`<div><strong>${label}</strong><p>${esc(conciseCopy(value,18))}</p></div>`).join('')+(data.platforms?.length?`<div class="strategy-summary-platforms">${data.platforms.map(movePlatform).join(' ')}</div>`:'');
}
function fillStrategy(data){
 strategyData={...data};
 strategyDescription=data.description||[data.goal,data.audience&&'Audience: '+data.audience,data.offer&&'Offer: '+data.offer].filter(Boolean).join('\n');
 document.getElementById('strategyBrief').value=strategyDescription;
 document.getElementById('strategyDirection').value=data.content_direction??[data.themes,data.rhythm,data.resources,data.avoid&&'Avoid: '+data.avoid].filter(Boolean).join('\n');
 strategyInputSnapshot=JSON.stringify(strategyInputs());
 updateStrategySearchPreview();strategySummary();
}
function updateStrategySearchPreview(){document.getElementById('strategySearchPreview').textContent=strategyData.themes||'No topics — evergreen ideas only';}
function setStrategySaved(saved){
 document.getElementById('strategyConfirmedState').textContent=saved?'Saved to your brand':'';
 document.getElementById('saveStrategyButton').hidden=saved;
 document.getElementById('strategyNextMoveButton').hidden=!saved;
 document.getElementById('strategyReviewHeading').textContent=saved?'Your strategy':'Your proposed strategy';
 document.getElementById('buildStrategyButton').textContent=hasConfirmedStrategy?'Update my strategy':'Shape my strategy ✦';
}
function strategyStepHint(){document.getElementById('strategyStepHint').textContent='';}
function strategyInputChanged(){
 document.getElementById('strategyConfirmedState').textContent='Unsaved changes';
 document.getElementById('strategyForm').hidden=true;
 document.getElementById('buildStrategyButton').hidden=false;
}
function chooseStrategyGoal(topic){
 const field=document.getElementById('strategyDirection');
 if(!field.value.toLowerCase().includes(topic.toLowerCase()))field.value=[field.value.trim(),topic].filter(Boolean).join(' · ');
 field.focus();strategyInputChanged();strategyStatus('');
}
document.querySelectorAll('[data-strategy-goal]').forEach(button=>button.addEventListener('click',()=>chooseStrategyGoal(button.dataset.strategyGoal)));
function strategyProposalBrief(){
 const brief=strategyInputs().brief;
 if(brief.length<3){document.getElementById('strategyBrief').focus();throw Error('Describe your business or goal first.');}
 if(brief.length>20000)throw Error('Please shorten your description to 20,000 characters. Your text is still here.');
 return brief;
}
['strategyBrief','strategyDirection'].forEach(id=>document.getElementById(id).addEventListener('input',strategyInputChanged));

document.getElementById('strategyPanel').addEventListener('close',()=>{strategyViewEpoch++;strategyPending=false;});
async function strategyTask(button,work){
 if(strategyPending)return;
 const operation=++strategyOperation,epoch=strategyViewEpoch;
 strategyPending=true;if(button)button.disabled=true;strategyStatus('Working…');
 document.getElementById('strategyPanel').setAttribute('aria-busy','true');
 try{await work(epoch);}catch(e){if(epoch===strategyViewEpoch){if(e.status===409){strategyLoaded=false;moveItems=[];moveIndex=0;renderNextMove();}strategyStatus(e.message||'Could not finish. Your saved work and input are kept.');}}
 finally{if(button)button.disabled=false;if(operation===strategyOperation){strategyPending=false;document.getElementById('strategyPanel').setAttribute('aria-busy','false');}}
}
function setPlanningView(planning){
 strategyPlanning=planning;
 document.getElementById('nextMoveSettings').hidden=!planning;
 document.getElementById('strategyActions').hidden=planning;
 document.getElementById('seriesDetails').hidden=true;
 document.getElementById('strategyTitleText').textContent=planning?'Your strategy':'Next move';
 document.getElementById('strategyClose').setAttribute('aria-label',planning?'Close your strategy':'Close next move');
 document.getElementById('strategyStepHint').hidden=!planning;
 document.getElementById('strategyEditLink').hidden=planning;
 document.getElementById('recommendationHelp').hidden=true;
 document.getElementById('recommendButton').hidden=planning||moveItems.length>0||!(hasConfirmedStrategy||quickMoveRequest);
}
function clearNextMoveDisplay(){
 document.getElementById('strategyActions').innerHTML='';
 document.getElementById('strategySourceNote').textContent='';
 document.getElementById('strategyPerformanceNote').hidden=true;
 document.getElementById('recommendationHelp').hidden=true;
}
async function openNextMove(planning=false){
 strategyViewEpoch++;strategyPending=false;
 setPlanningView(planning);clearNextMoveDisplay();strategyStatus('Loading…');
 const panel=document.getElementById('strategyPanel');if(!panel.open)panel.showModal();
 await strategyTask(null,async epoch=>{
  const data=await api('/api/strategy');if(epoch!==strategyViewEpoch)return;
  const reloadPlan=!strategyLoaded||data.revision!==strategyRevision;
  if(data.revision!==strategyRevision){moveItems=[];moveIndex=0;moveOffset=0;quickMoveRequest=null;}
  strategyRevision=data.revision;hasConfirmedStrategy=Boolean(data.confirmed.goal);
  const proposal=data.proposal.strategy;
  document.getElementById('strategyForm').hidden=!(proposal||hasConfirmedStrategy);
  if(reloadPlan)fillStrategy(proposal||data.confirmed.goal&&data.confirmed||data.defaults);
  if(reloadPlan){setStrategySaved(hasConfirmedStrategy&&!proposal);document.getElementById('buildStrategyButton').hidden=Boolean(proposal||hasConfirmedStrategy);}
  showStrategyAssumptions(data.proposal.assumptions||[]);

  if(!reloadPlan&&JSON.stringify(strategyInputs())!==strategyInputSnapshot)strategyInputChanged();
  strategyLoaded=true;setPlanningView(planning);
  if(planning){strategyStatus('');return;}
  const items=await loadNextMoves(epoch);if(epoch!==strategyViewEpoch||!items)return;
  if(hasConfirmedStrategy&&(!items.length||items.every(a=>a.stale&&!a.draft_id))){
   strategyStatus('Finding your next post…');
   await requestMoves(epoch);
  }
  if(epoch===strategyViewEpoch)strategyStatus('');
 });
}
document.getElementById('seriesDetails').addEventListener('toggle',event=>{if(event.target.open&&!event.target.hidden)strategyTask(null,loadSeries);});
function showStrategyAssumptions(items){document.getElementById('strategyAssumptions').innerHTML=items.length?'<p class="support-note"><strong>Check:</strong> '+items.slice(0,2).map(item=>esc(conciseCopy(item,16))).join(' ')+'</p>':'';}
async function proposeStrategy(button){await strategyTask(button,async epoch=>{
 const brief=strategyProposalBrief(),input={...strategyInputs(),brief},snapshot=JSON.stringify(input);
 const r=await api('/api/strategy/propose',{method:'POST',headers,body:JSON.stringify({...input,revision:strategyRevision})});
 if(epoch!==strategyViewEpoch)return;
 strategyRevision=r.revision;moveItems=[];moveIndex=0;moveOffset=0;quickMoveRequest=null;clearNextMoveDisplay();
 if(JSON.stringify(strategyInputs())!==snapshot){strategyLoaded=false;strategyStatus('Your newer text is kept. Update again to include it.');return;}
 fillStrategy({...r.proposal.strategy,description:brief,content_direction:input.content_direction});showStrategyAssumptions(r.proposal.assumptions||[]);
 document.getElementById('strategyForm').hidden=false;document.getElementById('buildStrategyButton').hidden=true;
 document.getElementById('strategyReviewHeading').focus();setStrategySaved(false);strategyStatus('');
});}
async function confirmStrategy(event){event.preventDefault();await strategyTask(event.submitter,async epoch=>{
 if(JSON.stringify(strategyInputs())!==strategyInputSnapshot)throw Error('Update your strategy first to include your latest description.');
 const snapshot=strategyInputSnapshot,strategy={...strategyData,description:strategyInputs().brief,content_direction:strategyInputs().content_direction};
 const r=await api('/api/strategy/confirm',{method:'POST',headers,body:JSON.stringify({strategy,revision:strategyRevision})});
 if(epoch!==strategyViewEpoch)return;
 strategyRevision=r.revision;hasConfirmedStrategy=true;moveItems=[];moveIndex=0;moveOffset=0;quickMoveRequest=null;clearNextMoveDisplay();
 if(JSON.stringify(strategyInputs())!==snapshot){strategyLoaded=false;strategyStatus('Strategy saved. Your newer text is not saved yet.');return;}
 fillStrategy(r.confirmed||strategy);showStrategyAssumptions([]);setStrategySaved(true);strategyStatus('Strategy saved.');
});}
function recommendationBody(fresh=false){
 const selected=moveItems[moveIndex]?.strategy_context;
 const topic=selected?.one_off?{brief:selected.topic||selected.goal,platforms:selected.platforms}:quickMoveRequest;
 return {revision:strategyRevision,post_only:true,fresh,...(topic||{})};
}
async function requestMoves(epoch=strategyViewEpoch,fresh=false,append=false,extra={}){
 const data=await api('/api/strategy/recommend',{method:'POST',headers,body:JSON.stringify({...recommendationBody(fresh),...extra})});
 if(epoch!==strategyViewEpoch)return;
 if(Array.isArray(data.items))return applyNextMoves(data,epoch,append,true);
 return loadNextMoves(epoch);
}
async function quickNextMove(button){await strategyTask(button,async epoch=>{
 const field=document.getElementById('quickMoveBrief'),brief=field.value.trim();
 const platforms=Array.from(document.querySelectorAll('[name=quick_move_platform]:checked'),n=>n.value);
 if(brief.length<3){field.focus();throw Error('Add a short topic for your next post.');}
 if(!platforms.length)throw Error('Choose a platform.');
 quickMoveRequest={brief,platforms};strategyStatus('Finding your next post…');
 await requestMoves(epoch);if(epoch===strategyViewEpoch){document.getElementById('recommendButton').hidden=true;strategyStatus('');}
});}
async function openSeriesPanel(){
 strategyViewEpoch++;strategyPending=false;setPlanningView(false);
 document.getElementById('strategyTitleText').textContent='Recurring posts';
 document.getElementById('strategyActions').hidden=true;document.getElementById('strategyEditLink').hidden=true;
 document.getElementById('recommendButton').hidden=true;document.getElementById('recommendationHelp').hidden=true;
 document.getElementById('seriesDetails').hidden=false;document.getElementById('seriesDetails').open=true;
 const panel=document.getElementById('strategyPanel');if(!panel.open)panel.showModal();
 await strategyTask(null,async()=>{await loadSeries();strategyStatus('');});
}

function moveEvidenceNotes(){const source=document.getElementById('strategySourceNote').textContent,performance=document.getElementById('strategyPerformanceNote');return (source?'<p>'+esc(source)+'</p>':'')+(!performance.hidden?'<p>'+performance.innerHTML+'</p>':'');}
function nextMoveSource(a){
 if(!a.source)return '<p class="source-kind">Evergreen · based on your strategy</p>';
 const s=a.source;
 return `<details class="source-evidence"><summary class="source-kind">${a.stale?(a.draft_id?'Saved source':'Refresh needed'):s.kind==='public_social'?'Recent social discussion':'Recent web coverage'} · Source</summary><p><a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(s.title)}</a></p><small>Reported publication: ${esc(s.published_at)} · Checked ${esc(new Date(s.checked_at).toLocaleString())}</small>${a.stale&&!a.draft_id?'<p>This source needs a fresh check before creating a draft.</p>':''}${moveEvidenceNotes()}</details>`;
}
function moveReason(text){return String(text||'').replace(/\s*\(strategy:[^)]*\)/gi,'').trim();}
function linkedDraftId(value){const id=Number(value);return Number.isSafeInteger(id)&&id>0?id:0;}
function nextMoveCard(a){
 const draftId=linkedDraftId(a.draft_id),stale=a.stale&&!draftId;
 const label=draftId?'Open draft':stale?'Refresh idea':'Draft post';
 const action=draftId?`draftNextMove(${a.id},this,${draftId})`:stale?'refreshStrategyActions(this)':`draftNextMove(${a.id},this)`;
 return `<article class="next-move next-move-featured">
 <div class="move-hero"><div class="move-meta"><span class="move-platform">${movePlatform(a.platform)}${a.platform==='instagram'?' · '+esc(a.format==='story'?'Story':'Post'):''}</span><span class="move-eyebrow">POST PROPOSAL</span></div>
 <h3 tabindex="-1">${esc(conciseCopy(a.title,14))}</h3>
 ${stale?'<p class="move-stale">Check the source before drafting.</p>':''}
 <div class="move-actions"><button class="button primary move-draft" onclick="${action}">${label}<span aria-hidden="true">→</span></button></div></div>
 <section class="move-recommendation" aria-labelledby="moveRecommendation${a.id}"><h4 id="moveRecommendation${a.id}">✦ AI recommendation</h4><p>${esc(conciseCopy(moveReason(a.reason),32))}</p>${a.source?nextMoveSource(a):'<small>'+esc(a.basis||('Based on your '+(a.strategy_context?.one_off?'topic':'strategy')))+'</small>'}<details class="move-refine"><summary>Refine idea</summary><label class="visually-hidden" for="moveFeedback${a.id}">What would you change?</label><textarea id="moveFeedback${a.id}" rows="2" maxlength="500" placeholder="More personal, less filming…" oninput="moveRefinements.set(${a.id},this.value)">${esc(moveRefinements.get(a.id)||'')}</textarea><button type="button" class="quiet-button" onclick="refineMove(${a.id},this)">Update idea →</button></details></section>
 <div class="move-pager" role="group" aria-label="Browse ideas"><button type="button" onclick="changeMove(-1,this)" aria-label="Previous idea" ${moveIndex===0?'disabled':''}>←</button><span role="status">Idea ${moveOffset+moveIndex+1}</span><button class="move-next" type="button" onclick="changeMove(1,this)" aria-label="Next idea">Next idea <span aria-hidden="true">→</span></button></div>
 </article>`;
}
function renderNextMove(){
 moveIndex=Math.max(0,Math.min(moveIndex,moveItems.length-1));
 document.getElementById('strategyActions').innerHTML=moveItems.length?nextMoveCard(moveItems[moveIndex]):(hasConfirmedStrategy?'<div class="move-empty"><h3>Your next post starts here</h3><button class="button primary" onclick="refreshStrategyActions(this)">Find an idea</button></div>':`<div class="move-empty"><h3>What are you posting about?</h3><label for="quickMoveBrief" class="visually-hidden">Topic for your next post</label><textarea id="quickMoveBrief" rows="3" maxlength="2000" placeholder="A new product, a useful tip, a day behind the scenes…">${esc(quickMoveRequest?.brief||'')}</textarea><fieldset><legend>Platform</legend>${['instagram','tiktok','x','facebook'].map(p=>`<label class="inline-choice"><input type="radio" name="quick_move_platform" value="${p}" ${(quickMoveRequest?.platforms||[]).includes(p)?'checked':''}>${movePlatform(p)}</label>`).join('')}</fieldset><button class="button primary" onclick="quickNextMove(this)">Find my next post</button></div>`);
}
async function changeMove(direction,button){
 if(strategyPending||!moveItems.length)return;
 if(direction<0){if(moveIndex===0)return;moveIndex--;renderNextMove();}
 else if(moveIndex<moveItems.length-1){moveIndex++;renderNextMove();}
 else {await strategyTask(button,async epoch=>{
  strategyStatus('Finding fresh ideas…');
  const items=await requestMoves(epoch,true,true);if(epoch!==strategyViewEpoch)return;
  if(!items?.length)throw Error('No fresh ideas yet. Try Next idea again.');
  renderNextMove();strategyStatus('');
 });}
 document.querySelector('#strategyActions h3')?.focus();
}
function applyNextMoves(data,epoch=strategyViewEpoch,append=false,selectNew=false){
 if(epoch!==strategyViewEpoch)return;
 if(Number.isInteger(data.revision)&&data.revision!==strategyRevision){moveItems=[];moveIndex=0;renderNextMove();strategyLoaded=false;const error=Error('Your strategy changed. Reopen Next move to see the latest ideas.');error.status=409;throw error;}
 document.getElementById('strategySourceNote').textContent=data.source_note||'';
 const note=document.getElementById('strategyPerformanceNote');note.hidden=!data.performance_note;
 note.innerHTML=data.performance_note?esc(data.performance_note)+' <a href="/analytics">View performance</a>':'';
 const currentId=moveItems[moveIndex]?.id;
 const items=data.items.filter(a=>a.kind!=='review');
 const context=items[0]?.strategy_context;
 if(context?.one_off)quickMoveRequest={brief:context.topic||context.goal,platforms:context.platforms};
 const history=(Array.isArray(data.history)?data.history:[]).filter(a=>a.kind!=='review');
 const merged=new Map((append?moveItems:history).map(a=>[a.id,a]));
 for(const item of [...history,...items])merged.set(item.id,item);
 const all=Array.from(merged.values()).sort((a,b)=>a.id-b.id),removed=Math.max(0,all.length-60);
 moveOffset=append?moveOffset+removed:0;moveItems=all.slice(-60);
 const preferred=append||selectNew?items[0]?.id:currentId;
 const kept=moveItems.findIndex(a=>a.id===preferred);
 moveIndex=kept<0?Math.max(0,moveItems.findIndex(a=>a.id===items[0]?.id)):kept;renderNextMove();
 document.getElementById('recommendationHelp').hidden=true;
 document.getElementById('recommendButton').hidden=strategyPlanning||moveItems.length>0||!(hasConfirmedStrategy||quickMoveRequest);
 document.getElementById('recommendButton').setAttribute('aria-label',items.length?'Refresh ideas':'Find post ideas');
 return items;
}
async function loadNextMoves(epoch=strategyViewEpoch){const data=await api('/api/strategy/actions');return applyNextMoves(data,epoch);}
async function refreshStrategyActions(button){await strategyTask(button,async epoch=>{strategyStatus('Finding your next post…');await requestMoves(epoch,true);if(epoch===strategyViewEpoch){moveOffset=0;strategyStatus('');renderNextMove();}});}
async function actionFeedback(id,status,button,extra={}){await strategyTask(button,async epoch=>{
 await api(`/api/strategy/actions/${id}/feedback`,{method:'POST',headers,body:JSON.stringify({status,reason:'',...extra})});
 if(epoch!==strategyViewEpoch)return;
 const items=await loadNextMoves(epoch);if(epoch!==strategyViewEpoch||!items)return;
 if(!items.length&&(hasConfirmedStrategy||quickMoveRequest)&&status!=='snoozed'){strategyStatus('Finding your next post…');await requestMoves(epoch);}
 if(epoch!==strategyViewEpoch)return;
 strategyStatus(status==='snoozed'?'Reminder saved. Nothing is scheduled to post.':'');
 document.querySelector('#strategyActions h3')?.focus();
});}
async function remindMove(id,days,button){
 const date=days===null?new Date(document.getElementById('moveReminder'+id).value):new Date();
 if(days!==null)date.setDate(date.getDate()+days);
 if(!Number.isFinite(date.getTime())||date<=new Date())return strategyStatus('Choose a future date and time.');
 await actionFeedback(id,'snoozed',button,{remind_at:date.toISOString()});
}
async function refineMove(id,button){await strategyTask(button,async epoch=>{
 const field=document.getElementById('moveFeedback'+id),refinement=field.value.trim();
 if(!refinement){field.focus();throw Error('Tell Zova what to change.');}
 moveRefinements.set(id,refinement);strategyStatus('Shaping your idea…');
 await requestMoves(epoch,true,true,{refine_action_id:id,refinement});
 if(epoch===strategyViewEpoch){if(moveRefinements.get(id)===refinement){moveRefinements.delete(id);strategyStatus('');}else strategyStatus('Your newer change is kept with the previous idea.');}
});}
async function openLinkedDraft(url,button,existingDraftId=0){
 if(sendingMessage||mediaUploading||studioLoading){strategyStatus('Finish the current upload or response first.');return;}
 await strategyTask(button,async()=>{
  const epoch=workspaceEpoch,draftId=linkedDraftId(existingDraftId);await saveDraftNow();if(epoch!==workspaceEpoch)return;studioBusy(true);strategyStatus(draftId?'Opening your draft…':'Writing your post…');
  try{const r=draftId?{draft_id:draftId}:await api(url,{method:'POST',headers,body:'{}'});if(epoch!==workspaceEpoch){strategyStatus('Post saved in Schedule. Your current chat is unchanged.');return;}const target=linkedDraftId(r.draft_id);if(!target)throw Error('Could not open this draft. Try again.');studioBusy(false);strategyStatus('Opening your draft…');location.assign(window.zovaWorkspaceUrl('/studio?draft='+target));}finally{if(epoch===workspaceEpoch)studioBusy(false);}
 });
}
const draftNextMove=(id,button,draftId)=>openLinkedDraft(`/api/strategy/actions/${id}/draft`,button,draftId);
async function openSeriesBuilder(){
 if(sendingMessage||mediaUploading)return strategyStatus('Finish the current response or upload first.');
 try{await saveDraftNow();if(!currentDraftId||!lastBrief.trim())throw Error('Create a draft with a brief first.');seriesRequestKey=crypto.randomUUID();document.getElementById('seriesBuilder').hidden=false;strategyStatus('Choose a rhythm. Dates remain unapproved until each post is reviewed.');}catch(e){strategyStatus(e.message);}
}
function seriesBody(){return {draft_id:currentDraftId,request_key:seriesRequestKey,start:document.getElementById('seriesStart').value,timezone:document.getElementById('seriesTimezone').value,frequency:document.getElementById('seriesFrequency').value,count:+document.getElementById('seriesCount').value,mode:document.getElementById('seriesMode').value,weekdays:Array.from(document.querySelectorAll('[name=series_day]:checked'),n=>+n.value)};}
async function previewSeries(button){await strategyTask(button,async()=>{const body=seriesBody();const r=await api('/api/series/preview',{method:'POST',headers,body:JSON.stringify(body)});seriesPreviewBody=JSON.stringify(body);document.getElementById('seriesPreview').innerHTML=`<p>${esc(r.note)}</p><ol>${r.times.map(t=>`<li>${esc(t.local.replace('T',' '))}</li>`).join('')}</ol><button class="button primary" onclick="createSeries(this)">Create draft series</button>`;strategyStatus('Check the dates and offsets.');});}
async function createSeries(button){await strategyTask(button,async()=>{if(JSON.stringify(seriesBody())!==seriesPreviewBody)throw Error('Settings changed. Preview the dates again.');await api('/api/series',{method:'POST',headers,body:seriesPreviewBody});document.getElementById('seriesBuilder').hidden=true;document.getElementById('seriesPreview').innerHTML='';await loadSeries();strategyStatus('Series saved. Each occurrence needs review before sending.');});}
async function loadSeries(){const rows=await api('/api/series');document.getElementById('seriesList').innerHTML=rows.map(s=>`<article class="next-move"><h3>${esc(s.spec.frequency)} ${esc(s.spec.mode)} drafts · ${esc(s.status)}</h3><p>${esc(s.spec.timezone)}</p>${s.status!=='cancelled'?`<button class="quiet-button" onclick="changeSeries(${s.id},${s.revision},'${s.status==='paused'?'resume':'pause'}',this)">${s.status==='paused'?'Resume':'Pause'}</button><button class="quiet-button" onclick="changeSeries(${s.id},${s.revision},'cancel',this)">Cancel series</button>`:''}${s.status==='active'&&s.spec.mode==='repeat'?`<button class="quiet-button" onclick="reviewRepeat(${s.id},${s.revision},this)">Review repeat schedule</button><div id="repeatReview${s.id}"></div>`:''}<ol>${s.occurrences.map(o=>`<li><p>${esc(new Date(o.due_at).toLocaleString(undefined,{timeZone:s.spec.timezone}))} · ${esc(o.status)}</p>${s.status==='active'&&o.status!=='cancelled'?`<button class="quiet-button" onclick="openLinkedDraft('/api/series/occurrences/${o.id}/draft',this,${linkedDraftId(o.draft_id)})">${o.draft_id?'Open draft':'Start draft'}</button><button class="quiet-button" onclick="cancelOccurrence(${o.id},${s.revision},this)">Cancel occurrence</button><details><summary>Change time</summary><label>New local time<input type="datetime-local" id="occTime${o.id}"></label><label>Applies to<select id="occScope${o.id}"><option value="one">This occurrence</option><option value="future">This and future occurrences</option></select></label><button class="quiet-button" onclick="moveOccurrence(${o.id},${s.revision},this)">Save new time</button></details>`:''}</li>`).join('')}</ol></article>`).join('')||'<p>No recurring series yet.</p>';}
async function changeSeries(id,revision,action,button){await strategyTask(button,async()=>{const r=await api(`/api/series/${id}/state`,{method:'POST',headers,body:JSON.stringify({revision,action})});await loadSeries();strategyStatus(r.note);});}
async function moveOccurrence(id,revision,button){await strategyTask(button,async()=>{const r=await api(`/api/series/occurrences/${id}/time`,{method:'POST',headers,body:JSON.stringify({revision,local_time:document.getElementById('occTime'+id).value,scope:document.getElementById('occScope'+id).value})});await loadSeries();strategyStatus(r.note);});}

async function cancelOccurrence(id,revision,button){await strategyTask(button,async()=>{await api(`/api/series/occurrences/${id}/cancel`,{method:'POST',headers,body:JSON.stringify({revision})});await loadSeries();strategyStatus('Occurrence cancelled.');});}

const repeatApprovals=new Map();
async function reviewRepeat(id,revision,button){await strategyTask(button,async()=>{
 const r=await api(`/api/series/${id}/review`,{method:'POST',headers,body:JSON.stringify({revision})});repeatApprovals.set(id,r.token);
 document.getElementById('repeatReview'+id).innerHTML=`<p>${esc(r.note)}</p>${r.occurrences.map(v=>{const s=v.snapshot;return `<details><summary>${esc(new Date(s.scheduled_utc).toLocaleString(undefined,{timeZone:s.timezone}))} · ${esc(s.timezone)}</summary>${Object.entries(s.targets).map(([p,t])=>`<h4>${esc(platformName(p))} ${esc(t.format_label||'')} · ${esc(t.display_name||t.username||t.account_id)}</h4><p>Account ${esc(t.account_id)}</p>${t.format==='story'?'<p>Only this visual publishes. Planning text is not included.</p>':''}${t.posts.map(text=>`<p class="review-copy">${esc(text)}</p>`).join('')}${t.link?`<p>${esc(t.link)}</p>`:''}`).join('')}<div class="review-media">${s.media.map(mediaPreview).join('')}</div></details>`;}).join('')}<button class="button primary" onclick="confirmRepeat(${id},this)">Confirm these ${r.occurrences.length} scheduled occurrences</button>`;
 strategyStatus('Review every occurrence before confirming.');
});}
async function confirmRepeat(id,button){await strategyTask(button,async()=>{
 const token=repeatApprovals.get(id);if(!token)throw Error('Review this series again.');
 const r=await api(`/api/series/${id}/confirm`,{method:'POST',headers,body:JSON.stringify({token})});repeatApprovals.delete(id);await loadSeries();strategyStatus(r.results.map(x=>'Draft '+x.draft_id+': '+x.status.replaceAll('_',' ')+(x.error?' — '+x.error:'')).join('. '));
});}

if(window.addEventListener)window.addEventListener('DOMContentLoaded',()=>{
 const query=new URLSearchParams(location.search);
 if(query.get('strategy')==='1')openNextMove(true);
 else if(query.get('series')==='1')openSeriesPanel();
});
