/* Progressive disclosure: the default Studio remains a conversation. */
let hasConfirmedStrategy=false;
let strategyRevision=0, strategyLoaded=false, strategyPending=false, seriesRequestKey=null, seriesPreviewBody=null;
const strategyKeys=['goal','audience','offer','voice','themes','rhythm','resources','avoid'];
const strategyStatus=text=>{document.getElementById('strategyStatus').textContent=text;};
function fillStrategy(data){strategyKeys.forEach(k=>document.getElementById('strategy_'+k).value=data[k]||'');document.querySelectorAll('[name=strategy_platform]').forEach(n=>n.checked=(data.platforms||[]).includes(n.value));}
async function strategyTask(button,work){
 if(strategyPending)return;
 strategyPending=true;if(button)button.disabled=true;strategyStatus('Working…');
 try{await work();}catch(e){strategyStatus(e.message||'Could not save. Your input is still here.');}
 finally{strategyPending=false;if(button)button.disabled=false;}
}
async function openNextMove(){
 document.getElementById('strategyPanel').showModal();
 if(strategyLoaded)return;
 await strategyTask(null,async()=>{
  const data=await api('/api/strategy');strategyRevision=data.revision;hasConfirmedStrategy=Boolean(data.confirmed.goal);document.getElementById('strategyForm').hidden=!(data.proposal.strategy||hasConfirmedStrategy);document.getElementById('recommendButton').hidden=!hasConfirmedStrategy;
  fillStrategy(data.proposal.strategy||data.confirmed.goal&&data.confirmed||data.defaults);
  document.getElementById('strategyConfirmedState').textContent=data.confirmed.goal?'A confirmed strategy is saved. Edits below only apply when you confirm.':'No confirmed strategy yet. Add your goal or ask Zova for a proposal.';
  showStrategyAssumptions(data.proposal.assumptions||[]);
  document.getElementById('strategyDetails').open=!data.confirmed.goal;
  await loadNextMoves();await loadSeries();strategyLoaded=true;strategyStatus('');
 });
}
function showStrategyAssumptions(items){document.getElementById('strategyAssumptions').innerHTML=items.length?'<p><b>Proposed assumptions — check before confirming</b></p><ul>'+items.map(x=>`<li>${esc(x)}</li>`).join('')+'</ul>':'';}
async function proposeStrategy(button){await strategyTask(button,async()=>{
 const r=await api('/api/strategy/propose',{method:'POST',headers,body:JSON.stringify({brief:document.getElementById('strategyBrief').value,revision:strategyRevision})});
 strategyRevision=r.revision;document.getElementById('strategyForm').hidden=false;fillStrategy(r.proposal.strategy);showStrategyAssumptions(r.proposal.assumptions);strategyStatus('Proposal ready. Check the details and confirm to use it.');
});}
async function confirmStrategy(event){event.preventDefault();await strategyTask(event.submitter,async()=>{
 const strategy=Object.fromEntries(strategyKeys.map(k=>[k,document.getElementById('strategy_'+k).value]));strategy.platforms=Array.from(document.querySelectorAll('[name=strategy_platform]:checked'),n=>n.value);
 const r=await api('/api/strategy/confirm',{method:'POST',headers,body:JSON.stringify({strategy,revision:strategyRevision})});strategyRevision=r.revision;hasConfirmedStrategy=true;document.getElementById('recommendButton').hidden=false;showStrategyAssumptions([]);
 document.getElementById('strategyConfirmedState').textContent='Confirmed strategy saved.';document.getElementById('strategyDetails').open=false;strategyStatus('Strategy saved. Preparing your next moves…');try{await api('/api/strategy/recommend',{method:'POST',headers,body:'{}'});await loadNextMoves();strategyStatus('Strategy saved. Choose your next move.');}catch(e){await loadNextMoves();strategyStatus('Strategy saved. Suggestions are unavailable right now; use Suggest next moves to retry.');}
});}
async function loadNextMoves(){const data=await api('/api/strategy/actions');document.getElementById('strategyActions').innerHTML=data.items.length?data.items.map(a=>`<article class="next-move"><h3>${esc(a.title)}</h3><p>${esc(a.reason)}</p><small>${esc(platformName(a.platform))}${a.platform==='instagram'?' '+esc(a.format):''} · ${esc(a.effort)}</small>${a.needs?`<p>Needed: ${esc(a.needs)}</p>`:''}<div><button class="button primary" onclick="draftNextMove(${a.id},this)">${a.draft_id?'Open draft':'Draft this'}</button><details><summary>More options</summary><button class="quiet-button" onclick="actionFeedback(${a.id},'complete',this)">Done</button><button class="quiet-button" onclick="actionFeedback(${a.id},'snoozed',this)">Tomorrow</button><button class="quiet-button" onclick="actionFeedback(${a.id},'dismissed',this)">Dismiss</button><label>Optional feedback<select id="actionReason${a.id}"><option value="">Choose a reason</option>${['Not relevant','Too much effort','Bad timing','Already done'].map(s=>`<option>${s}</option>`).join('')}</select></label></details></div></article>`).join(''):(hasConfirmedStrategy?'<p>No next moves ready. Ask for suggestions or review your strategy.</p>':'<p>Start with your goal. Zova will propose a strategy and next steps.</p>');}
async function refreshStrategyActions(button){await strategyTask(button,async()=>{await api('/api/strategy/recommend',{method:'POST',headers,body:'{}'});await loadNextMoves();strategyStatus('Choose an idea to draft, or adjust your strategy.');});}
async function actionFeedback(id,status,button){await strategyTask(button,async()=>{await api(`/api/strategy/actions/${id}/feedback`,{method:'POST',headers,body:JSON.stringify({status,reason:document.getElementById('actionReason'+id).value})});await loadNextMoves();strategyStatus(status==='snoozed'?'Snoozed for 24 hours.':'Feedback saved.');});}
async function openLinkedDraft(url,button){
 if(sendingMessage||mediaUploading||studioLoading){strategyStatus('Finish the current upload or response first.');return;}
 await strategyTask(button,async()=>{
  await saveDraftNow();studioBusy(true);
  try{const r=await api(url,{method:'POST',headers,body:'{}'});studioBusy(false);location.assign(window.zovaWorkspaceUrl('/studio?draft='+r.draft_id));}finally{studioBusy(false);}
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
