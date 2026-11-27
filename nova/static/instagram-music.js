/* Optional music never changes a destination or publishes a post. */
window.zovaInstagramMusic=(()=>{
 let choice=null,tracks=[],requestSerial=0,connectionId=null;
 const dialog=()=>document.getElementById('instagramMusic');
 const status=message=>{document.getElementById('instagramMusicStatus').textContent=message;};
 const eligibleFormat=()=>instagramFormat()==='post'&&uploadedMedia.length===1&&uploadedMediaKind==='video';
 function update(){
  const button=document.getElementById('instagramMusicButton');if(!button)return;
  button.hidden=!selectedPlatforms().includes('instagram');
  button.textContent=choice?'Music · '+choice.title:'Music options';
  const selected=document.getElementById('instagramMusicSelected');
  selected.hidden=!choice;
  document.getElementById('instagramMusicName').textContent=choice?choice.title+(choice.artist?' · '+choice.artist:''):'';
  if(choice)for(const key of ['audio_volume','video_volume'])document.getElementById('instagram_'+key).value=choice[key];
 }
 function changed(){update();scheduleAutosave();}
 function renderExports(){
  const host=document.getElementById('instagramMusicMedia');host.replaceChildren();
  for(const media of uploadedMedia){
   const a=document.createElement('a');a.className='button quiet';a.href=window.zovaWorkspaceUrl('/media/download/'+media.id);a.download=media.filename||'Zova-media';a.textContent='Save '+(media.filename||'media');host.append(a);
  }
  document.getElementById('instagramCopyCaption').hidden=!variants.instagram?.posts?.length||instagramFormat()==='story';
 }
 async function search(event){
  event?.preventDefault();if(!eligibleFormat())return;
  const serial=++requestSerial,epoch=workspaceEpoch;
  const button=document.getElementById('instagramMusicSearchButton');button.disabled=true;
  status('Checking available music…');document.getElementById('instagramMusicResults').replaceChildren();
  try{
   const query=new URLSearchParams({q:document.getElementById('instagramMusicQuery').value,audio_type:'music'});
   if(connectionId)query.set('connection_id',connectionId);
   const data=await api('/api/instagram/audio?'+query);
   if(serial!==requestSerial||epoch!==workspaceEpoch||!dialog().open)return;
   connectionId=data.connection_id||connectionId;tracks=data.tracks||[];
   const accounts=data.accounts||[],selector=document.getElementById('instagramMusicAccount');
   document.getElementById('instagramMusicAccountLabel').hidden=accounts.length<2;
   selector.innerHTML=accounts.map(account=>`<option value="${Number(account.id)}" ${Number(account.id)===Number(connectionId)?'selected':''}>${esc(account.name)}</option>`).join('');
   status(data.eligible?(tracks.length?'Choose a track. Instagram adds it when the Reel publishes.':'No matching music. Try another search.'):data.reason);
   document.getElementById('instagramFinish').open=!data.eligible;
   document.getElementById('instagramMusicSearch').hidden=!data.eligible;
   document.getElementById('instagramMusicResults').innerHTML=tracks.map((track,index)=>`<div class="music-track"><button type="button" data-track="${index}"><strong>${esc(track.title)}</strong><span>${esc(track.artist)}</span></button>${track.preview_url?`<a href="${esc(track.preview_url)}" target="_blank" rel="noopener" aria-label="Preview ${esc(track.title)} on Instagram">Listen ↗</a>`:''}</div>`).join('');
  }catch(error){if(serial===requestSerial&&epoch===workspaceEpoch)status(error.message);}
  finally{if(serial===requestSerial)button.disabled=false;}
 }
 async function open(){
  requestSerial++;connectionId=choice?.connection_id||null;tracks=[];
  document.getElementById('postSettings').close();dialog().showModal();update();renderExports();
  document.getElementById('instagramMusicResults').replaceChildren();
  document.getElementById('instagramMusicAccountLabel').hidden=true;
  document.getElementById('instagramMusicSearch').hidden=!eligibleFormat();
  document.getElementById('instagramFinish').open=!eligibleFormat();
  status(eligibleFormat()?'Checking music access…':'Instagram adds music to photos and Stories.');
  if(eligibleFormat())await search();
 }
 function clear(){choice=null;changed();status('Original video audio will be kept.');}
 function optionFor(destination){
  if(!choice)return null;
  if(!eligibleFormat())throw Error('Your selected music needs a single video Reel. Remove the music or switch back to Post with one video.');
  if(Number(destination)!==Number(choice.connection_id))throw Error('Choose music for this Instagram account before reviewing.');
  const {connection_id,...audio}=choice;return audio;
 }
 document.addEventListener('DOMContentLoaded',()=>{
  document.getElementById('instagramMusicSearch').addEventListener('submit',search);
  document.getElementById('instagramMusicAccount').addEventListener('change',event=>{connectionId=Number(event.target.value);choice=null;changed();search();});
  document.getElementById('instagramMusicResults').addEventListener('click',event=>{
   const button=event.target.closest('[data-track]');if(!button||!editableDraft())return;
   const track=tracks[Number(button.dataset.track)];if(!track)return;
   choice={connection_id:Number(connectionId),audio_id:track.audio_id,title:track.title,artist:track.artist,audio_volume:100,video_volume:100};changed();status('Music selected. Check the track and volumes in your final review.');
  });
  for(const key of ['audio_volume','video_volume'])document.getElementById('instagram_'+key).addEventListener('change',event=>{if(choice){const volume=Number(event.target.value);if(!Number.isInteger(volume)||volume<1||volume>100){event.target.value=choice[key];status('Choose a volume from 1 to 100.');return;}choice[key]=volume;changed();}});
  dialog().addEventListener('close',()=>{requestSerial++;document.getElementById('instagramMusicSearchButton').disabled=false;});
  document.getElementById('instagramCopyCaption').addEventListener('click',async()=>{try{await navigator.clipboard.writeText(variants.instagram.posts.join('\n\n'));status('Caption copied. Paste it in Instagram after adding your media.');}catch{status('Select the caption in Studio to copy it.');}});
  update();
 });
 return {open,clear,update,optionFor,snapshot:()=>choice?{...choice}:null,restore:value=>{requestSerial++;choice=value&&typeof value==='object'?{...value}:null;update();},reset:()=>{requestSerial++;choice=null;update();}};
})();
