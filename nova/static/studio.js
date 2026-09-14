let variants = {};

let currentPlatform = "x";

let currentDraftId = null;

let uploadedMediaIds = [];

let uploadedMediaKind = null;

let uploadedMedia = [];

let uploadedVideoDuration = 0;

let mediaUploadVersion = 0;

let mediaUploading = false;

let reviewMode = "publish";

let reviewContexts = {};

let conversation = [];

let lastBrief = "";

let pendingSchedule = null;

let autosaveTimer = null;

let autosaveInFlight = null;

let currentDraftStatus = "draft";

const headers = {"Content-Type":"application/json","X-Zova-Request":"1"};



const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c]));

const selectedPlatforms = () => [...document.querySelectorAll(".platform-check input:checked")].map(input => input.value);

const platformName = value => value === "x" ? "X" : value === "tiktok" ? "TikTok" : value.charAt(0).toUpperCase() + value.slice(1);

const platformIcon = platform => platform === "x" ? '<svg class="inline-social-icon x x-logo" viewBox="0 0 24 24" aria-hidden="true"><path d="M18.24 2.25h3.31l-7.23 8.26 8.5 11.24h-6.66l-5.21-6.82-5.97 6.82H1.67l7.74-8.84L1.25 2.25h6.83l4.71 6.23 5.45-6.23Zm-1.16 17.52h1.83L7.08 4.13H5.12l11.96 15.64Z"/></svg>' : platform === "instagram" ? '<span class="inline-social-icon instagram">IG</span>' : platform === "facebook" ? '<span class="inline-social-icon facebook">f</span>' : '<span class="inline-social-icon tiktok">♪</span>';



async function api(url,options={}){
  const response=await fetch(url,options),text=await response.text();let payload;
  try{payload=JSON.parse(text);}catch{payload={detail:response.status===401?'Sign in again to continue. Your changes are still visible.':'The server could not complete that request. Please retry.'};}
  if(!response.ok){const error=new Error(typeof payload.detail==='string'?payload.detail:'Check the entered details and try again.');error.status=response.status;throw error;}return payload;
}
function busy(button,active,label){button.disabled=active;if(active){button.dataset.old=button.textContent;button.textContent=label;}else button.textContent=button.dataset.old||button.textContent;}

let stickToLatest=true;
function scrollChat(force=false){const feed=document.getElementById('chatFeed');if(force||stickToLatest){requestAnimationFrame(()=>feed.scrollTo({top:feed.scrollHeight,behavior:'smooth'}));document.getElementById('latestMessage').hidden=true;}else document.getElementById('latestMessage').hidden=false;}
document.getElementById('chatFeed').addEventListener('scroll',()=>{const feed=document.getElementById('chatFeed');stickToLatest=feed.scrollHeight-feed.scrollTop-feed.clientHeight<100;if(stickToLatest)document.getElementById('latestMessage').hidden=true;});

function addUserMessage(text){document.querySelector('.welcome-message')?.remove();conversation.push({role:"user",content:text});document.getElementById("chatFeed").insertAdjacentHTML("beforeend",`<article class="chat-message user-message"><div class="message-content">${esc(text)}</div></article>`);scrollChat();}

function addThinking(){document.getElementById("chatFeed").insertAdjacentHTML("beforeend",'<article id="thinking" class="chat-message assistant-message"><div class="assistant-avatar">Z</div><div class="message-content"><div class="thinking" role="status" aria-label="Zova is thinking"><i></i><i></i><i></i></div></div></article>');scrollChat();}

function removeThinking(){document.getElementById("thinking")?.remove();}

function looksLikeInsight(text){return /\b(analytics?|performance|trend|trending|impressions?|views?|likes?|comments?|repl(?:y|ies)|shares?|reposts?|followers?|engagement|what(?:'s| is) working|best post|recent posts?|strategy)\b/i.test(text);}

function looksLikeNewPost(text){return /\b(create|write|draft|prepare|turn this|new post|announce|post about|add (?:an? )?(?:x|twitter|instagram|facebook|tiktok) version)\b/i.test(text)||/\bmake (?:a|an|some) (?:x|twitter|instagram|facebook|tiktok|social )?(?:post|caption|thread)\b/i.test(text);}

function platformsFromText(text){const explicit=[];if(/\b(x|twitter)\b/i.test(text))explicit.push("x");if(/\b(insta|instagram)\b/i.test(text))explicit.push("instagram");if(/\bfacebook\b/i.test(text))explicit.push("facebook");if(/\btiktok\b/i.test(text))explicit.push("tiktok");return explicit.length?[...new Set(explicit)]:selectedPlatforms();}



function platformMention(text){const lower=text.toLowerCase();if(/\b(insta|instagram)\b/.test(lower)&&variants.instagram)return"instagram";if(/\bfacebook\b/.test(lower)&&variants.facebook)return"facebook";if(/\btiktok\b/.test(lower)&&variants.tiktok)return"tiktok";if(/\b(x|twitter)\b/.test(lower)&&variants.x)return"x";return null;}

function draftWorkspace(){
 const platforms=Object.keys(variants),locked=!editableDraft(),missing=['x','instagram','facebook','tiktok'].filter(p=>!variants[p]);
 return `<section class="inline-draft" data-current-draft>${platforms.length>1?`<div class="draft-tabs" role="tablist" aria-label="Platform versions">${platforms.map(p=>`<button class="draft-tab ${p===currentPlatform?'active':''}" role="tab" aria-selected="${p===currentPlatform}" onclick="switchPlatform('${p}')">${platformName(p)}</button>`).join('')}</div>`:`<p class="response-note">${platformName(currentPlatform)}</p>`}<div id="variantEditor">${editorMarkup()}</div><div class="response-actions">${!locked?`<button onclick="${editingDraft?'finishEditing()':"canvasView('edit')"}">${editingDraft?'Done editing':'Edit'}</button>`:''}<button onclick="copyDraft(this)">Copy</button>${!locked?`<button class="review-button" onclick="requestPublishConfirmation('publish')">Review & publish</button>`:''}<details class="draft-options"><summary>More</summary><div><button onclick="canvasView('preview')">Preview</button>${platforms.length>1?`<button onclick="canvasView('compare')">Compare versions</button>`:''}${!locked?`<button onclick="undoTextEdit()">Undo text edit</button><button onclick="requestPublishConfirmation('schedule')">Schedule</button>${missing.map(p=>`<button onclick="promptComposer('Add a ${platformName(p)} version of this post')">Add ${platformName(p)}</button>`).join('')}`:''}</div></details></div>${locked?`<p class="response-note">${esc(publicationStates[currentPlatform]?publicationStatus(publicationStates[currentPlatform]):'Not submitted')}</p>`:''}</section>`;
}

function editorMarkup(){if(!editingDraft||!editableDraft())return `<div class="draft-text">${(variants[currentPlatform]?.posts||[]).map((post,index)=>`${(variants[currentPlatform]?.posts.length||0)>1?`<small>Post ${index+1}</small>`:''}<p>${esc(post)}</p>`).join('')}</div>`;const posts=(variants[currentPlatform]||{}).posts||[],locked=!editableDraft(),rule=currentPlatform==="x"?"280 characters max per post":(["instagram","tiktok"].includes(currentPlatform)?"Media required to publish":"Review before publishing");return `<div class="draft-platform-head"><b>${platformIcon(currentPlatform)} ${platformName(currentPlatform)}</b><span>${rule}</span></div>${posts.map((post,index)=>`<label class="post-copy"><span>${posts.length>1?`Post ${index+1}`:"Draft"}</span><textarea rows="${posts.length>1?4:6}" ${locked?"readonly":""} onfocus="rememberTextRevision()" oninput="updateDraftPost('${currentPlatform}',${index},this.value)">${esc(post)}</textarea><small>${currentPlatform==="x"?`<b data-character-count>${post.length}</b> / 280`:saveLabel}</small></label>`).join("")}`;}

function saveEditors(){return saveDraftNow();}

function updateCount(){}

function renderAttachments(){
  if(typeof renderReadiness==='function'){renderReadiness();renderCanvasPreview();}

  const tray=document.getElementById("attachmentTray");

  tray.classList.toggle("hidden",!uploadedMedia.length);

  tray.innerHTML=uploadedMedia.map((asset,index)=>`<div class="attachment-card">${!asset.url?'<div class="attachment-placeholder">Preview unavailable</div>':asset.kind==="video"?`<video src="${esc(asset.url)}" controls preload="metadata" aria-label="Preview of ${esc(asset.filename)}"></video>`:`<img src="${esc(asset.url)}" alt="Preview of ${esc(asset.filename)}">`}<div class="attachment-details"><span title="${esc(asset.filename)}">${esc(asset.filename)}</span><button type="button" onclick="removeAttachment(${index})" ${mediaUploading?"disabled":""} aria-label="Remove ${esc(asset.filename)}">Remove</button></div></div>`).join("");

  document.getElementById("mediaStatus").textContent=uploadedMedia.length?(uploadedMediaKind==="video"?"Video attached · Instagram and TikTok only":`${uploadedMedia.length} image${uploadedMedia.length===1?"":"s"} attached`):"";

}

function removeAttachment(index){

  if(mediaUploading||!editableDraft())return;

  uploadedMedia.splice(index,1);

  uploadedMediaIds=uploadedMedia.map(asset=>asset.id);

  uploadedMediaKind=uploadedMedia.length?(uploadedMedia.some(asset=>asset.kind==="video")?"video":"image"):null;

  if(uploadedMediaKind!=="video")uploadedVideoDuration=0;

  renderAttachments();scheduleAutosave();

}

async function uploadMedia(){

  const input=document.getElementById("mediaInput"),files=[...input.files],status=document.getElementById("mediaStatus");

  if(!files.length || mediaUploading || sendingMessage || !editableDraft())return;

  const videos=files.filter(file=>file.type.startsWith("video/"));

  input.value="";

  if(videos.length && files.length>1){status.textContent="Add one video at a time, without images.";return;}

  const version=++mediaUploadVersion;

  mediaUploading=true;input.disabled=true;renderAttachments();status.textContent="Uploading… Your current attachments stay selected until this finishes.";

  try{

    const duration=videos.length?await readVideoDuration(videos[0]):0;

    if(version!==mediaUploadVersion)return;

    const form=new FormData();files.forEach(file=>form.append("files",file));

    const result=await api("/api/media",{method:"POST",headers:{"X-Zova-Request":"1"},body:form});

    if(version!==mediaUploadVersion)return;

    uploadedMedia=result.assets;uploadedMediaIds=uploadedMedia.map(asset=>asset.id);

    uploadedMediaKind=uploadedMedia.some(asset=>asset.kind==="video")?"video":"image";

    uploadedVideoDuration=duration;

    if(uploadedMediaKind==="video"){document.getElementById("px").checked=false;document.getElementById("pfb").checked=false;}

    mediaUploading=false;renderAttachments();

  }catch(error){

    if(version===mediaUploadVersion){mediaUploading=false;renderAttachments();status.textContent=`Upload failed. ${error.message} Your previous attachment selection is unchanged.`;}

  }finally{

    if(version===mediaUploadVersion){mediaUploading=false;input.disabled=false;}

  }

}

function readVideoDuration(file){return new Promise(resolve=>{const video=document.createElement("video"),url=URL.createObjectURL(file);let done=false;const finish=value=>{if(done)return;done=true;clearTimeout(timer);URL.revokeObjectURL(url);resolve(value);};const timer=setTimeout(()=>finish(0),10000);video.preload="metadata";video.onloadedmetadata=()=>finish(Number.isFinite(video.duration)?video.duration:0);video.onerror=()=>finish(0);video.src=url;});}

function validateVideoPlatforms(platforms){return uploadedMediaKind!=="video"||platforms.every(p=>["instagram","tiktok"].includes(p));}



/* Conversational publish flow: the composer is the only text/date input surface. */

async function publishSelected(){await requestPublishConfirmation("publish");}

async function scheduleSelected(){await suggestSchedule();}

function useTime(value,label){addUserMessage(`Schedule these posts for ${label}`);requestPublishConfirmation("schedule",value);}



async function loadSidebar(){try{const data=await api("/api/analytics"),s=data._summary||{};const connected=Object.entries(data).filter(([k,v])=>k!=="_summary"&&v.connected);document.getElementById("connectionPulse").innerHTML=`<i></i>${connected.length?`${connected.length} social${connected.length===1?"":"s"} connected`:"Connect your socials"}`;document.getElementById("analytics").innerHTML=`<div class="pulse-metrics"><div><strong>${(s.impressions==null?"—":Number(s.impressions).toLocaleString())}</strong><span>Views / impressions</span></div><div><strong>${(s.likes==null?"—":Number(s.likes).toLocaleString())}</strong><span>Likes</span></div><div><strong>${(s.comments==null?"—":Number(s.comments).toLocaleString())}</strong><span>Comments</span></div><div><strong>${(s.shares==null?"—":Number(s.shares).toLocaleString())}</strong><span>Shares</span></div></div><p class="support-note">Available recent-post totals; — means unavailable.</p><a class="analytics-link" href="/analytics">Open full analytics →</a><button class="ask-data" onclick="askQuestion('What is working across my accounts?')">Ask in chat</button>`;}catch(error){document.getElementById("analytics").innerHTML=`<div class="tiny-error">${esc(error.message)}</div>`;}try{const feed=await api("/api/recent-posts"),rows=feed.posts||[];document.getElementById("recentActivity").innerHTML=rows.length?rows.slice(0,4).map(row=>`<a class="recent-post" target="_blank" rel="noopener" href="${esc(row.url||"#")}">${row.image_url?`<img src="${esc(row.image_url)}" alt="">`:`<span class="post-platform-art">${platformIcon(row.platform)}</span>`}<div class="recent-post-copy"><div class="recent-post-platform">${platformIcon(row.platform)}<b>${platformName(row.platform)}</b></div><p>${esc(row.text||"Media post").slice(0,90)}</p><div class="post-metrics"><span>♥ ${(row.likes==null?"—":Number(row.likes).toLocaleString())}</span><span>◯ ${(row.comments==null?"—":Number(row.comments).toLocaleString())}</span><span>↗ ${(row.shares==null?"—":Number(row.shares).toLocaleString())}</span></div></div></a>`).join(""):'<div class="empty-feed">Your recent posts will appear here.</div>';}catch(error){document.getElementById("recentActivity").innerHTML=`<div class="tiny-error">${esc(error.message)}</div>`;}}


function askQuestion(text){document.getElementById("brief").value=text;sendMessage();}

function useStarter(button){const text=button.textContent;if(text==="Create posts from an idea"){document.getElementById("brief").placeholder="Tell Zova the idea, source or announcement…";document.getElementById("brief").focus();return;}askQuestion(text);}
