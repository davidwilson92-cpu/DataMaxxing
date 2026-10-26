/* Keep linked settings and save errors reachable inside the grouped account. */
function revealAccountSection(){
 let target;
 try{target=document.getElementById(decodeURIComponent(location.hash.slice(1)));}catch(_){return;}
 if(!target)return;
 for(let parent=target;parent;parent=parent.parentElement){
  if(parent.tagName==='DETAILS')parent.open=true;
 }
 target.scrollIntoView({block:'start'});
}
window.addEventListener('hashchange',revealAccountSection);
revealAccountSection();

// Show the saved profile immediately, without replacing edits made during a scan.
const voiceScan=document.getElementById('rescanVoice');
if(voiceScan)voiceScan.addEventListener('click',async()=>{
 const out=document.getElementById('scanResult'),form=document.getElementById('voicePreferences');
 const fields=['writing_tone','audience','topics','things_to_avoid','example_posts','preferred_post_length'];
 const before=Object.fromEntries(fields.map(name=>[name,form.elements.namedItem(name)?.value]));
 voiceScan.disabled=true;voiceScan.textContent='Scanning…';out.hidden=false;out.textContent='';
 try{
  const response=await fetch('/api/voice/scan-socials',{method:'POST'}),data=await response.json();
  if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:'Could not scan. Your saved voice is unchanged.');
  if(data.status!=='learned'){out.textContent=data.message;return;}
  if(!data.preferences)throw new Error('Could not display the saved voice. Reload Account to check it.');
  let keptEdits=false;
  fields.forEach(name=>{const field=form.elements.namedItem(name);if(!field)return;if(field.value===before[name])field.value=String(data.preferences[name]??'');else keptEdits=true;});
  document.getElementById('voiceStatusTitle').textContent='Voice saved';
  document.getElementById('voiceStatusText').textContent=data.preferences.writing_tone||'Your saved guidance is ready.';
  document.getElementById('voiceSavedAt').textContent='Saved just now.';
  out.textContent=`Learned from ${data.posts_scanned} captions. ${keptEdits?'Your unsaved edits are kept below; save them when ready.':data.overrides?.length?'Your own preferences were kept.':'Your saved voice is shown below.'}`;
 }catch(error){out.textContent=error.message||'Could not scan. Your saved voice is unchanged.';}
 finally{voiceScan.disabled=false;voiceScan.textContent='Scan recent posts';}
});
