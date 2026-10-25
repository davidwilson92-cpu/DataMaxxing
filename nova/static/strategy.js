/* Strategy is saved per brand; Next move is a separate, immediate action. */
let hasConfirmedStrategy=false;
let moveItems=[],moveIndex=0;
const movePlatform=p=>window.zovaPlatformLabel?window.zovaPlatformLabel(p):esc(platformName(p));
let strategyRevision=0,strategyLoaded=false,strategyPending=false,seriesRequestKey=null,seriesPreviewBody=null;
let strategyViewEpoch=0,strategyOperation=0,strategyPlanning=false,strategyDescription='',strategyFilledValues='',quickMoveRequest=null;
const strategyKeys=['goal','audience','offer','voice','themes','rhythm','resources','avoid'];
const strategyStatus=text=>{document.getElementById('strategyStatus').textContent=text;};
function strategySnapshot(){return Object.fromEntries(strategyKeys.map(k=>[k,document.getElementById('strategy_'+k).value]));}
function strategySummary(){
 const data=strategySnapshot(),rows=[['Goal',data.goal],['Audience',data.audience],['Content',data.themes],['Rhythm',data.rhythm]];
 const platforms=Array.from(document.querySelectorAll('[name=strategy_platform]:checked'),n=>movePlatform(n.value)).join(' ');
 document.getElementById('strategySummary').innerHTML=rows.filter(([,value])=>value).map(([label,value])=>`<div><strong>${label}</strong><p>${esc(value)}</p></div>`).join('')+(platforms?`<div><strong>Platforms</strong><p class="strategy-summary-platforms">${platforms}</p></div>`:'');
}
function fillStrategy(data){
 strategyKeys.forEach(k=>document.getElementById('strategy_'+k).value=data[k]||'');
 document.querySelectorAll('[name=strategy_platform]').forEach(n=>n.checked=(data.platforms||[]).includes(n.value));
 strategyFilledValues=JSON.stringify(strategySnapshot());
 strategyDescription=data.description||'';
 document.getElementById('strategyBrief').value=data.description||[data.goal,data.audience&&'Audience: '+data.audience,data.themes&&'Content: '+data.themes,data.rhythm&&'Rhythm: '+data.rhythm].filter(Boolean).join('\n');
 updateStrategySearchPreview();strategySummary();
}
function updateStrategySearchPreview(){document.getElementById('strategySearchPreview').textContent=document.getElementById('strategy_themes').value.trim()||'No topics — evergreen ideas only';}
function setStrategySaved(saved){
 document.getElementById('strategyConfirmedState').textContent=saved?'Saved to this brand. Edit whenever your direction changes.':'';
 document.getElementById('saveStrategyButton').hidden=saved;
 document.getElementById('strategyNextMoveButton').hidden=!saved;
 document.getElementById('strategyReviewHeading').textContent=saved?'Your strategy':'Your proposed strategy';
 document.getElementById('buildStrategyButton').textContent=hasConfirmedStrategy?'Update my strategy':'Build my strategy';
}
function showStrategyEditor(){
 document.getElementById('strategyQuickStart').hidden=true;
 document.getElementById('strategyReviseButton').hidden=false;
 document.getElementById('strategyForm').hidden=false;
 document.getElementById('strategyAdvanced').open=true;
 document.getElementById('strategy_goal').focus();setStrategySaved(false);
}
function editStrategyDescription(){
 document.getElementById('strategyQuickStart').hidden=false;
 document.getElementById('strategyForm').hidden=true;
 document.getElementById('strategyReviseButton').hidden=true;
 document.getElementById('strategyBrief').focus();strategyStatus('');
}
function strategyStepHint(state){document.getElementById('strategyStepHint').textContent=state==='proposal'?'Review, then save your strategy.':'';}
function chooseStrategyGoal(goal){
 const field=document.getElementById('strategyBrief');
 if(field.value.trim()){field.focus();strategyStatus('Edit your description here. Your existing text is kept.');return;}
 field.value=goal;field.focus();strategyStatus('');
}
document.querySelectorAll('[data-strategy-goal]').forEach(button=>button.addEventListener('click',()=>chooseStrategyGoal(button.dataset.strategyGoal)));
function strategyProposalBrief(){
 const brief=document.getElementById('strategyBrief').value.trim();
 if(brief.length<3){document.getElementById('strategyBrief').focus();throw Error('Describe your business or goal first.');}
 if(brief.length>20000)throw Error('Please shorten your description to 20,000 characters. Your text is still here.');
 return brief;
}
document.getElementById('strategy_themes').addEventListener('input',updateStrategySearchPreview);
document.querySelectorAll('#strategyForm textarea, #strategyForm input').forEach(field=>field.addEventListener('input',()=>{setStrategySaved(false);strategySummary();}));
document.getElementById('strategyBrief').addEventListener('input',()=>{
 document.getElementById('strategyConfirmedState').textContent='Changes are not saved. Update your strategy to apply them.';
});
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
 document.getElementById('recommendButton').hidden=planning||!(hasConfirmedStrategy||quickMoveRequest);
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
  if(data.revision!==strategyRevision){moveItems=[];moveIndex=0;quickMoveRequest=null;}
  strategyRevision=data.revision;hasConfirmedStrategy=Boolean(data.confirmed.goal);
  const proposal=data.proposal.strategy;
  document.getElementById('strategyForm').hidden=!(proposal||hasConfirmedStrategy);
  if(reloadPlan)fillStrategy(proposal||data.confirmed.goal&&data.confirmed||data.defaults);
  if(reloadPlan){setStrategySaved(hasConfirmedStrategy&&!proposal);document.getElementById('strategyQuickStart').hidden=Boolean(proposal||hasConfirmedStrategy);document.getElementById('strategyReviseButton').hidden=!(proposal||hasConfirmedStrategy);}
  showStrategyAssumptions(data.proposal.assumptions||[]);
  document.getElementById('strategyManualEdit').hidden=Boolean(proposal||hasConfirmedStrategy);
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
function showStrategyAssumptions(items){document.getElementById('strategyAssumptions').innerHTML=items.length?'<p class="support-note"><strong>Please check:</strong> '+items.map(esc).join(' ')+'</p>':'';}
async function proposeStrategy(button){await strategyTask(button,async epoch=>{
 const brief=strategyProposalBrief();
 const r=await api('/api/strategy/propose',{method:'POST',headers,body:JSON.stringify({brief,revision:strategyRevision})});
 if(epoch!==strategyViewEpoch)return;
 strategyRevision=r.revision;moveItems=[];moveIndex=0;quickMoveRequest=null;clearNextMoveDisplay();
 if(document.getElementById('strategyBrief').value.trim()!==brief){strategyLoaded=false;strategyStatus('A proposal was saved. Your newer description is kept; update again when ready.');return;}
 fillStrategy({...r.proposal.strategy,description:brief});showStrategyAssumptions(r.proposal.assumptions||[]);
 document.getElementById('strategyQuickStart').hidden=true;document.getElementById('strategyReviseButton').hidden=false;
 document.getElementById('strategyForm').hidden=false;document.getElementById('strategyAdvanced').open=false;
 document.getElementById('strategyReviewHeading').focus();document.getElementById('strategyManualEdit').hidden=true;setStrategySaved(false);strategyStatus('');
});}
async function confirmStrategy(event){event.preventDefault();await strategyTask(event.submitter,async epoch=>{
 const strategy=strategySnapshot();strategy.description=strategyDescription;
 strategy.platforms=Array.from(document.querySelectorAll('[name=strategy_platform]:checked'),n=>n.value);
 // A changed description must be applied before an older AI proposal can be saved.
 if(strategyDescription&&document.getElementById('strategyBrief').value.trim()!==strategyDescription)throw Error('Update your strategy first to include your latest description.');
 if(JSON.stringify(strategySnapshot())!==strategyFilledValues){
  strategy.description=strategyKeys.filter(key=>strategy[key]).map(key=>key==='goal'?strategy[key]:key[0].toUpperCase()+key.slice(1)+': '+strategy[key]).join('\n')+'\nPlatforms: '+strategy.platforms.join(', ');
 }
 const r=await api('/api/strategy/confirm',{method:'POST',headers,body:JSON.stringify({strategy,revision:strategyRevision})});
 if(epoch!==strategyViewEpoch)return;
 strategyRevision=r.revision;hasConfirmedStrategy=true;moveItems=[];moveIndex=0;quickMoveRequest=null;clearNextMoveDisplay();
 fillStrategy(r.confirmed||strategy);showStrategyAssumptions([]);strategyStepHint('confirmed');setStrategySaved(true);
 document.getElementById('strategyQuickStart').hidden=true;document.getElementById('strategyReviseButton').hidden=false;
 document.getElementById('strategyAdvanced').open=false;strategyStatus('Strategy saved.');
});}
function recommendationBody(){return {revision:strategyRevision,...(quickMoveRequest||{})};}
async function requestMoves(epoch=strategyViewEpoch){
 const data=await api('/api/strategy/recommend',{method:'POST',headers,body:JSON.stringify(recommendationBody())});
 if(epoch!==strategyViewEpoch)return;
 if(Array.isArray(data.items))return applyNextMoves(data,epoch);
 return loadNextMoves(epoch);
}
async function quickNextMove(button){await strategyTask(button,async epoch=>{
 const field=document.getElementById('quickMoveBrief'),brief=field.value.trim();
 const platforms=Array.from(document.querySelectorAll('[name=quick_move_platform]:checked'),n=>n.value);
 if(brief.length<3){field.focus();throw Error('Add a short topic for your next post.');}
 if(!platforms.length)throw Error('Choose a platform.');
 quickMoveRequest={brief,platforms};strategyStatus('Finding your next post…');
 await requestMoves(epoch);if(epoch===strategyViewEpoch){document.getElementById('recommendButton').hidden=false;strategyStatus('');}
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
 const review=a.kind==='review',draftId=linkedDraftId(a.draft_id),stale=a.stale&&!draftId;
 const label=draftId?'Open draft':stale?'Refresh idea':review?'See steps':'Draft post';
 const action=draftId?`draftNextMove(${a.id},this,${draftId})`:stale?'refreshStrategyActions(this)':review?`showMoveSteps(${a.id})`:`draftNextMove(${a.id},this)`;
 return `<article class="next-move next-move-featured">
 <div class="move-hero">
 <div class="move-meta"><span class="move-platform">${movePlatform(a.platform)}${a.platform==='instagram'?' · '+esc(a.format==='story'?'Story':'Post'):''}</span></div>
 <h3 tabindex="-1">${esc(a.title)}</h3>
 ${stale?'<p class="move-stale">Refresh the source before drafting.</p>':''}
 <div class="move-actions"><button class="button primary move-draft" onclick="${action}">${label}<span aria-hidden="true">→</span></button></div>
 </div>
 <div class="move-pager" role="group" aria-label="Browse ideas"><button type="button" onclick="changeMove(-1)" aria-label="Previous idea" ${moveItems.length<2?'disabled':''}>←</button><span role="status">${moveIndex+1} of ${moveItems.length}</span><button type="button" onclick="changeMove(1)" aria-label="Next idea" ${moveItems.length<2?'disabled':''}>→</button></div>
 <section class="move-context move-open-section" id="moveDetails${a.id}" aria-labelledby="moveDetailsHeading${a.id}"><h4 id="moveDetailsHeading${a.id}" tabindex="-1">Details</h4>
 <div class="move-detail-body">${review?`<div class="move-review-steps"><p>${esc(a.brief)}</p><button class="quiet-button" onclick="actionFeedback(${a.id},'complete',this)">Mark done</button></div>`:''}<p>${esc(moveReason(a.reason))}</p>${a.needs?`<p><strong>To make it:</strong> ${esc(a.needs)}</p>`:''}${a.source?nextMoveSource(a):'<details class="source-evidence"><summary class="source-kind">'+(a.strategy_context?.one_off?'Based on your topic':'Based on your strategy')+' · not a live trend</summary>'+moveEvidenceNotes()+'</details>'}</div></section>
 <section class="move-feedback move-open-section" aria-labelledby="moveFeedbackHeading${a.id}"><h4 id="moveFeedbackHeading${a.id}">Change this idea</h4><div class="move-feedback-input"><input id="moveFeedback${a.id}" aria-label="What to change about this idea" maxlength="80" placeholder="Less filming, more tips…"><button class="quiet-button" onclick="refineMove(${a.id},this)" aria-label="Apply your feedback">→</button></div><button class="quiet-button" onclick="actionFeedback(${a.id},'dismissed',this)">Skip idea</button></section>
 </article>`;
}
function showMoveSteps(id){const details=document.getElementById('moveDetails'+id);details.querySelector('h4')?.focus();details.scrollIntoView({block:'nearest'});}
function renderNextMove(){
 moveIndex=Math.max(0,Math.min(moveIndex,moveItems.length-1));
 document.getElementById('strategyActions').innerHTML=moveItems.length?nextMoveCard(moveItems[moveIndex]):(hasConfirmedStrategy?'<div class="move-empty"><h3>Your next post starts here</h3><button class="button primary" onclick="refreshStrategyActions(this)">Find an idea</button></div>':`<div class="move-empty"><h3>What are you posting about?</h3><label for="quickMoveBrief" class="visually-hidden">Topic for your next post</label><textarea id="quickMoveBrief" rows="3" maxlength="2000" placeholder="A new product, a useful tip, a day behind the scenes…">${esc(quickMoveRequest?.brief||'')}</textarea><fieldset><legend>Platform</legend>${['instagram','tiktok','x','facebook'].map(p=>`<label class="inline-choice"><input type="radio" name="quick_move_platform" value="${p}" ${(quickMoveRequest?.platforms||[]).includes(p)?'checked':''}>${movePlatform(p)}</label>`).join('')}</fieldset><button class="button primary" onclick="quickNextMove(this)">Find my next post</button></div>`);
}
function changeMove(direction){if(strategyPending||moveItems.length<2)return;moveIndex=(moveIndex+direction+moveItems.length)%moveItems.length;renderNextMove();document.querySelector('#strategyActions h3')?.focus();}
function applyNextMoves(data,epoch=strategyViewEpoch){
 if(epoch!==strategyViewEpoch)return;
 if(Number.isInteger(data.revision)&&data.revision!==strategyRevision){moveItems=[];moveIndex=0;renderNextMove();strategyLoaded=false;const error=Error('Your strategy changed. Reopen Next move to see the latest ideas.');error.status=409;throw error;}
 document.getElementById('strategySourceNote').textContent=data.source_note||'';
 const note=document.getElementById('strategyPerformanceNote');note.hidden=!data.performance_note;
 note.innerHTML=data.performance_note?esc(data.performance_note)+' <a href="/analytics">View performance</a>':'';
 const currentId=moveItems[moveIndex]?.id;
 const items=[...data.items].sort((a,b)=>(a.kind==='review')-(b.kind==='review'));
 const context=items[0]?.strategy_context;
 if(context?.one_off)quickMoveRequest={brief:context.goal,platforms:context.platforms};
 moveItems=items;const kept=items.findIndex(a=>a.id===currentId);moveIndex=kept<0?0:kept;renderNextMove();
 document.getElementById('recommendationHelp').hidden=true;
 document.getElementById('recommendButton').hidden=strategyPlanning||!(hasConfirmedStrategy||quickMoveRequest);
 document.getElementById('recommendButton').setAttribute('aria-label',items.length?'Refresh ideas':'Find post ideas');
 return items;
}
async function loadNextMoves(epoch=strategyViewEpoch){const data=await api('/api/strategy/actions');return applyNextMoves(data,epoch);}
async function refreshStrategyActions(button){await strategyTask(button,async epoch=>{strategyStatus('Finding your next post…');await requestMoves(epoch);if(epoch===strategyViewEpoch)strategyStatus('');});}
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
 const field=document.getElementById('moveFeedback'+id),reason=field.value.trim();
 if(!reason){field.focus();throw Error('Tell Zova what to change.');}
 await api(`/api/strategy/actions/${id}/feedback`,{method:'POST',headers,body:JSON.stringify({status:'dismissed',reason})});
 if(epoch!==strategyViewEpoch)return;
 moveItems=moveItems.filter(item=>item.id!==id);moveIndex=0;renderNextMove();
 strategyStatus('Finding a better fit…');await requestMoves(epoch);if(epoch===strategyViewEpoch)strategyStatus('');
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
