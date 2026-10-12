/* Progressive disclosure: the default Studio remains a conversation. */
let hasConfirmedStrategy=false;
let moveItems=[],moveIndex=0;
const movePlatform=p=>window.zovaPlatformLabel?window.zovaPlatformLabel(p):esc(platformName(p));
let strategyRevision=0, strategyLoaded=false, strategyPending=false, seriesRequestKey=null, seriesPreviewBody=null;
const strategyKeys=['goal','audience','offer','voice','themes','rhythm','resources','avoid'];
const strategyStatus=text=>{document.getElementById('strategyStatus').textContent=text;};
function fillStrategy(data){strategyKeys.forEach(k=>document.getElementById('strategy_'+k).value=data[k]||'');document.querySelectorAll('[name=strategy_platform]').forEach(n=>n.checked=(data.platforms||[]).includes(n.value));updateStrategySearchPreview();}
function updateStrategySearchPreview(){document.getElementById('strategySearchPreview').textContent=document.getElementById('strategy_themes').value.trim()||'None yet - suggestions will be evergreen';}
function showStrategyEditor(){document.getElementById('strategyForm').hidden=false;document.getElementById('strategyQuickStart').open=false;document.getElementById('strategyReviewHeading').focus();document.getElementById('strategyStepHint').textContent='Review your goal, audience and platforms. Confirm when the plan reflects your intentions.';}
function strategyStepHint(state){document.getElementById('strategyStepHint').textContent=state==='proposal'?'Check your plan, then confirm.':state==='confirmed'?'':'';}
function chooseStrategyGoal(goal){const field=document.getElementById('strategyBrief');if(!field.value.trim())field.value=goal;else if(!field.value.includes(goal)){const next=field.value.trim()+'\n'+goal;if(next.length>20000){strategyStatus('Your brief is full. Edit it before adding another goal; your text is unchanged.');field.focus();return;}field.value=next;}field.focus();strategyStatus('Goal added to your brief. Add any detail, then ask for a plan.');}
document.querySelectorAll('[data-strategy-goal]').forEach(button=>button.addEventListener('click',()=>chooseStrategyGoal(button.dataset.strategyGoal)));
function strategyProposalBrief(){
 const goal=document.getElementById('strategyBrief').value.trim();
 if(goal.length<3){document.getElementById('strategyBrief').focus();throw Error('Add a short goal or paste your strategy first.');}
 const audience=document.getElementById('strategyQuickAudience').value.trim(),time=document.getElementById('strategyQuickTime').value.trim();
 const brief=[goal,audience?'Audience: '+audience:'',time?'Time and resources: '+time:''].filter(Boolean).join('\n\n');
 if(brief.length>20000)throw Error('Please shorten your brief to 20,000 characters including audience and time. Your text is still here.');
 return brief;
}
document.getElementById('strategy_themes').addEventListener('input',updateStrategySearchPreview);
async function strategyTask(button,work){
 if(strategyPending)return;
 strategyPending=true;if(button)button.disabled=true;strategyStatus('Working…');
 try{await work();}catch(e){strategyStatus(e.message||'Could not save. Your input is still here.');}
 finally{strategyPending=false;if(button)button.disabled=false;}
}
function setPlanningView(planning){
 document.getElementById('nextMoveSettings').hidden=!planning;
 document.getElementById('strategyActions').hidden=planning;
 document.getElementById('strategyTitleText').textContent=planning?'Your plan':'Next move';
 document.getElementById('strategyClose').setAttribute('aria-label',planning?'Close your plan':'Close next move');
 document.getElementById('strategyStepHint').hidden=!planning;
}
async function openNextMove(planning=false){
 setPlanningView(planning);
 document.getElementById('strategyPanel').showModal();
 await strategyTask(null,async()=>{
  const data=await api('/api/strategy');const reloadPlan=!strategyLoaded||data.revision!==strategyRevision;strategyRevision=data.revision;hasConfirmedStrategy=Boolean(data.confirmed.goal);
  document.getElementById('strategyForm').hidden=!(data.proposal.strategy||hasConfirmedStrategy);
  document.getElementById('recommendButton').hidden=planning||!hasConfirmedStrategy;
  if(reloadPlan)fillStrategy(data.proposal.strategy||data.confirmed.goal&&data.confirmed||data.defaults);
  strategyStepHint(data.proposal.strategy?'proposal':hasConfirmedStrategy?'confirmed':'new');
  document.getElementById('strategyConfirmedState').textContent=data.proposal.strategy?'Review before saving. Your current plan stays in use.':'';
  showStrategyAssumptions(data.proposal.assumptions||[]);
  document.getElementById('strategyDetails').open=planning||!hasConfirmedStrategy;
  document.getElementById('nextMoveSettings').open=planning;document.getElementById('nextMoveSettingsLabel').hidden=true;
  document.getElementById('strategyQuickStart').open=!(data.proposal.strategy||hasConfirmedStrategy);
  document.getElementById('strategyManualEdit').hidden=Boolean(data.proposal.strategy||hasConfirmedStrategy);
  strategyLoaded=true;
  if(planning){strategyStatus('');return;}
  const items=await loadNextMoves();
  if(hasConfirmedStrategy&&(!items.length||items.every(a=>a.stale&&!a.draft_id))){
   strategyStatus('Finding your next post…');
   await api('/api/strategy/recommend',{method:'POST',headers,body:'{}'});
   await loadNextMoves();
  }
  strategyStatus('');
 });
}
document.getElementById('seriesDetails').addEventListener('toggle',event=>{
 if(event.target.open)strategyTask(null,loadSeries);
});
function showStrategyAssumptions(items){document.getElementById('strategyAssumptions').innerHTML=items.length?'<p><b>Proposed assumptions — check before confirming</b></p><ul>'+items.map(x=>`<li>${esc(x)}</li>`).join('')+'</ul>':'';}
async function proposeStrategy(button){await strategyTask(button,async()=>{
 const r=await api('/api/strategy/propose',{method:'POST',headers,body:JSON.stringify({brief:strategyProposalBrief(),revision:strategyRevision})});
 strategyRevision=r.revision;document.getElementById('strategyForm').hidden=false;fillStrategy(r.proposal.strategy);showStrategyAssumptions(r.proposal.assumptions);showStrategyEditor();strategyStepHint('proposal');document.getElementById('strategyManualEdit').hidden=true;strategyStatus('');
});}
async function confirmStrategy(event){event.preventDefault();await strategyTask(event.submitter,async()=>{
 const strategy=Object.fromEntries(strategyKeys.map(k=>[k,document.getElementById('strategy_'+k).value]));strategy.platforms=Array.from(document.querySelectorAll('[name=strategy_platform]:checked'),n=>n.value);
 const r=await api('/api/strategy/confirm',{method:'POST',headers,body:JSON.stringify({strategy,revision:strategyRevision})});strategyRevision=r.revision;hasConfirmedStrategy=true;strategyStepHint('confirmed');document.getElementById('recommendButton').hidden=false;showStrategyAssumptions([]);
 setPlanningView(false);document.getElementById('strategyConfirmedState').textContent='';document.getElementById('nextMoveSettings').open=false;document.getElementById('nextMoveSettingsLabel').hidden=true;document.getElementById('strategyDetails').open=false;strategyStatus('Strategy saved. Preparing your next moves…');try{await api('/api/strategy/recommend',{method:'POST',headers,body:'{}'});await loadNextMoves();strategyStatus('');}catch(e){await loadNextMoves();strategyStatus('Plan saved. Couldn’t load ideas. Try Find post ideas.');}
});}
function nextMoveSource(a){
 if(!a.source)return '<p class="source-kind">Evergreen · based on your strategy</p>';
 const s=a.source;
 return `<details class="source-evidence"><summary class="source-kind">${a.stale?(a.draft_id?'Saved source':'Refresh needed'):s.kind==='public_social'?'Recent social discussion':'Recent web coverage'} · Source</summary><p><a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(s.title)}</a></p><small>Reported publication: ${esc(s.published_at)} · Checked ${esc(new Date(s.checked_at).toLocaleString())}</small>${a.stale&&!a.draft_id?'<p>This source needs a fresh check before creating a draft.</p>':''}</details>`;
}
function moveReason(text){return String(text||'').replace(/\s*\(strategy:[^)]*\)/gi,'').trim();}
function nextMoveCard(a){
 const review=a.kind==='review',stale=a.stale&&!a.draft_id;
 const label=a.draft_id?'Open draft':stale?'Refresh idea':review?'See steps':'Draft post';
 const action=stale?'refreshStrategyActions(this)':review?`showMoveSteps(${a.id})`:`draftNextMove(${a.id},this)`;
 return `<article class="next-move next-move-featured">
 <div class="move-hero">
 <div class="move-meta"><span class="move-platform">${movePlatform(a.platform)}${a.platform==='instagram'?' · '+esc(a.format==='story'?'Story':'Post'):''}</span></div>
 <h3 tabindex="-1">${esc(a.title)}</h3>
 ${stale?'<p class="move-stale">Refresh the source before drafting.</p>':''}
 <div class="move-actions"><button class="button primary move-draft" onclick="${action}">${label}<span aria-hidden="true">→</span></button></div>
 </div>
 <div class="move-pager" role="group" aria-label="Browse ideas"><button type="button" onclick="changeMove(-1)" aria-label="Previous idea" ${moveItems.length<2?'disabled':''}>←</button><span role="status">${moveIndex+1} of ${moveItems.length}</span><button type="button" onclick="changeMove(1)" aria-label="Next idea" ${moveItems.length<2?'disabled':''}>→</button></div>
 <details class="move-context" id="moveDetails${a.id}"><summary>Details <span class="disclosure-chevron" aria-hidden="true">⌄</span></summary>
 <div class="move-detail-body">${review?`<div class="move-review-steps"><p>${esc(a.brief)}</p><button class="quiet-button" onclick="actionFeedback(${a.id},'complete',this)">Mark done</button></div>`:''}<p>${esc(moveReason(a.reason))}</p>${a.needs?`<p><strong>To make it:</strong> ${esc(a.needs)}</p>`:''}${a.effort?`<p class="move-effort">${esc(a.effort)}</p>`:''}${nextMoveSource(a)}</div></details>
 <details class="move-feedback"><summary>Change this idea <span class="disclosure-chevron" aria-hidden="true">⌄</span></summary><label for="moveFeedback${a.id}">What would work better?</label><input id="moveFeedback${a.id}" maxlength="80" placeholder="E.g. less filming, more tips for beginners"><button class="button primary" onclick="refineMove(${a.id},this)">Find a better idea</button><button class="quiet-button" onclick="actionFeedback(${a.id},'dismissed',this)">Not for me</button></details>
 </article>`;
}
function showMoveSteps(id){const details=document.getElementById('moveDetails'+id);details.open=true;details.querySelector('summary')?.focus();}
function renderNextMove(){
 moveIndex=Math.max(0,Math.min(moveIndex,moveItems.length-1));
 document.getElementById('strategyActions').innerHTML=moveItems.length?nextMoveCard(moveItems[moveIndex]):(hasConfirmedStrategy?'<div class="move-empty"><h3>Ready for a new idea?</h3><button class="button primary" onclick="refreshStrategyActions(this)">Find an idea</button></div>':'<div class="move-empty"><h3>Give your ideas a direction</h3><button class="button primary" onclick="openNextMove(true)">Set your goal</button></div>');
}
function changeMove(direction){if(strategyPending||moveItems.length<2)return;moveIndex=(moveIndex+direction+moveItems.length)%moveItems.length;renderNextMove();document.querySelector('#strategyActions h3')?.focus();}
async function loadNextMoves(){
 document.getElementById('recommendationHelp').hidden=!hasConfirmedStrategy;
 const data=await api('/api/strategy/actions');
 document.getElementById('strategySourceNote').textContent=data.source_note||'';
 const note=document.getElementById('strategyPerformanceNote');note.hidden=!data.performance_note;
 note.innerHTML=data.performance_note?esc(data.performance_note)+' <a href="/analytics">View performance</a>':'';
 const currentId=moveItems[moveIndex]?.id;
 const items=[...data.items].sort((a,b)=>(a.kind==='review')-(b.kind==='review'));
 moveItems=items;const kept=items.findIndex(a=>a.id===currentId);moveIndex=kept<0?0:kept;renderNextMove();
 document.getElementById('recommendButton').setAttribute('aria-label',items.length?'Refresh ideas':'Find post ideas');
 return items;
}
async function refreshStrategyActions(button){await strategyTask(button,async()=>{strategyStatus('Finding your next post…');await api('/api/strategy/recommend',{method:'POST',headers,body:'{}'});await loadNextMoves();strategyStatus('');});}
async function actionFeedback(id,status,button,extra={}){await strategyTask(button,async()=>{
 await api(`/api/strategy/actions/${id}/feedback`,{method:'POST',headers,body:JSON.stringify({status,reason:'',...extra})});
 const items=await loadNextMoves();
 if(!items.length&&hasConfirmedStrategy&&status!=='snoozed'){strategyStatus('Finding your next post…');await api('/api/strategy/recommend',{method:'POST',headers,body:'{}'});await loadNextMoves();}
 strategyStatus(status==='snoozed'?'Reminder saved. Nothing is scheduled to post.':'');
 document.querySelector('#strategyActions h3')?.focus();
});}
async function remindMove(id,days,button){
 const date=days===null?new Date(document.getElementById('moveReminder'+id).value):new Date();
 if(days!==null)date.setDate(date.getDate()+days);
 if(!Number.isFinite(date.getTime())||date<=new Date())return strategyStatus('Choose a future date and time.');
 await actionFeedback(id,'snoozed',button,{remind_at:date.toISOString()});
}
async function refineMove(id,button){await strategyTask(button,async()=>{
 const field=document.getElementById('moveFeedback'+id),reason=field.value.trim();
 if(!reason){field.focus();throw Error('Tell Zova what to change.');}
 await api(`/api/strategy/actions/${id}/feedback`,{method:'POST',headers,body:JSON.stringify({status:'dismissed',reason})});
 strategyStatus('Finding a better fit…');await api('/api/strategy/recommend',{method:'POST',headers,body:'{}'});moveIndex=0;await loadNextMoves();strategyStatus('');
});}
async function openLinkedDraft(url,button){
 if(sendingMessage||mediaUploading||studioLoading){strategyStatus('Finish the current upload or response first.');return;}
 await strategyTask(button,async()=>{
  const epoch=workspaceEpoch;await saveDraftNow();if(epoch!==workspaceEpoch)return;studioBusy(true);strategyStatus('Writing your post…');
  try{const r=await api(url,{method:'POST',headers,body:'{}'});if(epoch!==workspaceEpoch){strategyStatus('Post saved in Drafts. Your current chat is unchanged.');return;}studioBusy(false);strategyStatus('Opening your draft…');location.assign(window.zovaWorkspaceUrl('/studio?draft='+r.draft_id));}finally{if(epoch===workspaceEpoch)studioBusy(false);}
 });
}
const draftNextMove=(id,button)=>openLinkedDraft(`/api/strategy/actions/${id}/draft`,button);
document.getElementById('strategyImport').addEventListener('change',async event=>{
 const file=event.target.files[0];if(!file)return;
 try{if(!/\.(txt|md)$/i.test(file.name)||file.size>20000)throw Error('Use a UTF-8 .txt or .md file up to 20 KB. For PDF or Word, paste the relevant text.');const text=new TextDecoder('utf-8',{fatal:true}).decode(await file.arrayBuffer());document.getElementById('strategyBrief').value=text;strategyStatus('Text imported. Review it, then request a proposal.');}catch(e){strategyStatus(e.message||'This file could not be read. Paste your strategy instead.');}finally{event.target.value='';}
});
async function openSeriesBuilder(){
 if(sendingMessage||mediaUploading)return strategyStatus('Finish the current response or upload first.');
 try{await saveDraftNow();if(!currentDraftId||!lastBrief.trim())throw Error('Create a draft with a brief first.');seriesRequestKey=crypto.randomUUID();document.getElementById('seriesBuilder').hidden=false;strategyStatus('Choose a rhythm. Dates remain unapproved until each post is reviewed.');}catch(e){strategyStatus(e.message);}
}
function seriesBody(){return {draft_id:currentDraftId,request_key:seriesRequestKey,start:document.getElementById('seriesStart').value,timezone:document.getElementById('seriesTimezone').value,frequency:document.getElementById('seriesFrequency').value,count:+document.getElementById('seriesCount').value,mode:document.getElementById('seriesMode').value,weekdays:Array.from(document.querySelectorAll('[name=series_day]:checked'),n=>+n.value)};}
async function previewSeries(button){await strategyTask(button,async()=>{const body=seriesBody();const r=await api('/api/series/preview',{method:'POST',headers,body:JSON.stringify(body)});seriesPreviewBody=JSON.stringify(body);document.getElementById('seriesPreview').innerHTML=`<p>${esc(r.note)}</p><ol>${r.times.map(t=>`<li>${esc(t.local.replace('T',' '))}</li>`).join('')}</ol><button class="button primary" onclick="createSeries(this)">Create draft series</button>`;strategyStatus('Check the dates and offsets.');});}
async function createSeries(button){await strategyTask(button,async()=>{if(JSON.stringify(seriesBody())!==seriesPreviewBody)throw Error('Settings changed. Preview the dates again.');await api('/api/series',{method:'POST',headers,body:seriesPreviewBody});document.getElementById('seriesBuilder').hidden=true;document.getElementById('seriesPreview').innerHTML='';await loadSeries();strategyStatus('Series saved. Each occurrence needs review before sending.');});}
async function loadSeries(){const rows=await api('/api/series');document.getElementById('seriesList').innerHTML=rows.map(s=>`<article class="next-move"><h3>${esc(s.spec.frequency)} ${esc(s.spec.mode)} drafts · ${esc(s.status)}</h3><p>${esc(s.spec.timezone)}</p>${s.status!=='cancelled'?`<button class="quiet-button" onclick="changeSeries(${s.id},${s.revision},'${s.status==='paused'?'resume':'pause'}',this)">${s.status==='paused'?'Resume':'Pause'}</button><button class="quiet-button" onclick="changeSeries(${s.id},${s.revision},'cancel',this)">Cancel series</button>`:''}${s.status==='active'&&s.spec.mode==='repeat'?`<button class="quiet-button" onclick="reviewRepeat(${s.id},${s.revision},this)">Review repeat schedule</button><div id="repeatReview${s.id}"></div>`:''}<ol>${s.occurrences.map(o=>`<li><p>${esc(new Date(o.due_at).toLocaleString(undefined,{timeZone:s.spec.timezone}))} · ${esc(o.status)}</p>${s.status==='active'&&o.status!=='cancelled'?`<button class="quiet-button" onclick="openLinkedDraft('/api/series/occurrences/${o.id}/draft',this)">${o.draft_id?'Open draft':'Start draft'}</button><button class="quiet-button" onclick="cancelOccurrence(${o.id},${s.revision},this)">Cancel occurrence</button><details><summary>Change time</summary><label>New local time<input type="datetime-local" id="occTime${o.id}"></label><label>Applies to<select id="occScope${o.id}"><option value="one">This occurrence</option><option value="future">This and future occurrences</option></select></label><button class="quiet-button" onclick="moveOccurrence(${o.id},${s.revision},this)">Save new time</button></details>`:''}</li>`).join('')}</ol></article>`).join('')||'<p>No recurring series yet.</p>';}
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
