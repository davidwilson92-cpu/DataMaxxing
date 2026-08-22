let variants = {};
let currentPlatform = "x";
let currentDraftId = null;
let uploadedMediaIds = [];
let uploadedMediaKind = null;
let uploadedMedia = [];
let uploadedVideoDuration = 0;
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
const platformName = value => value === "x" ? "X" : value.charAt(0).toUpperCase() + value.slice(1);
const platformIcon = platform => platform === "x" ? '<svg class="inline-social-icon x x-logo" viewBox="0 0 24 24" aria-hidden="true"><path d="M18.24 2.25h3.31l-7.23 8.26 8.5 11.24h-6.66l-5.21-6.82-5.97 6.82H1.67l7.74-8.84L1.25 2.25h6.83l4.71 6.23 5.45-6.23Zm-1.16 17.52h1.83L7.08 4.13H5.12l11.96 15.64Z"/></svg>' : platform === "instagram" ? '<span class="inline-social-icon instagram">IG</span>' : platform === "facebook" ? '<span class="inline-social-icon facebook">f</span>' : '<span class="inline-social-icon tiktok">♪</span>';

async function api(url, options={}) { const response=await fetch(url,options); let payload; try{payload=await response.json();}catch{payload={detail:await response.text()};} if(!response.ok) throw new Error(payload.detail||"Request failed"); return payload; }
function busy(button,active,label){button.disabled=active;if(active){button.dataset.old=button.textContent;button.textContent=label;}else button.textContent=button.dataset.old||button.textContent;}
function scrollChat(){const feed=document.getElementById("chatFeed");requestAnimationFrame(()=>feed.scrollTo({top:feed.scrollHeight,behavior:"smooth"}));}
function addUserMessage(text){conversation.push({role:"user",content:text});document.getElementById("chatFeed").insertAdjacentHTML("beforeend",`<article class="chat-message user-message"><div class="message-content">${esc(text)}</div></article>`);scrollChat();}
function addAssistantMessage(text,extra=""){conversation.push({role:"assistant",content:text});document.getElementById("chatFeed").insertAdjacentHTML("beforeend",`<article class="chat-message assistant-message"><div class="assistant-avatar">${document.querySelector(".app-brand .zova-symbol")?.outerHTML||"Z"}</div><div class="message-content"><div class="message-name">Zova</div><p>${esc(text)}</p>${extra}</div></article>`);scrollChat();}
function addThinking(){document.getElementById("chatFeed").insertAdjacentHTML("beforeend",'<article id="thinking" class="chat-message assistant-message"><div class="assistant-avatar">Z</div><div class="message-content"><div class="thinking"><i></i><i></i><i></i></div></div></article>');scrollChat();}
function removeThinking(){document.getElementById("thinking")?.remove();}
function looksLikeInsight(text){return /\b(analytics?|performance|trend|trending|impressions?|views?|likes?|comments?|repl(?:y|ies)|shares?|reposts?|followers?|engagement|what(?:'s| is) working|best post|recent posts?|strategy)\b/i.test(text);}
function looksLikeNewPost(text){return /\b(create|write|draft|prepare|turn this|new post|announce|post about|add (?:an? )?(?:x|twitter|instagram|facebook|tiktok) version)\b/i.test(text)||/\bmake (?:a|an|some) (?:x|twitter|instagram|facebook|tiktok|social )?(?:post|caption|thread)\b/i.test(text);}
function platformsFromText(text){const explicit=[];if(/\b(x|twitter)\b/i.test(text))explicit.push("x");if(/\b(insta|instagram)\b/i.test(text))explicit.push("instagram");if(/\bfacebook\b/i.test(text))explicit.push("facebook");if(/\btiktok\b/i.test(text))explicit.push("tiktok");return explicit.length?[...new Set(explicit)]:selectedPlatforms();}

async function sendMessage(){
  const input=document.getElementById("brief"), text=input.value.trim(), button=document.getElementById("generateBtn");
  if(!text) return input.focus();
  addUserMessage(text); input.value=""; busy(button,true,"…"); addThinking();
  try{
    if(looksLikeInsight(text)){
      const result=await api("/api/insights",{method:"POST",headers,body:JSON.stringify({question:text})}); removeThinking(); addAssistantMessage(result.answer); return;
    }
    if(Object.keys(variants).length && /\b(schedule|best time|when should|publish time)\b/i.test(text)){
      removeThinking(); await suggestSchedule(text); return;
    }
    if(Object.keys(variants).length && /\b(publish|post (?:it|these|them)|send (?:it|these|them) live)\b/i.test(text)){
      removeThinking(); await requestPublishConfirmation("publish"); return;
    }
    const requestedPlatforms=platformsFromText(text);
    const missingPlatforms=requestedPlatforms.filter(platform=>!variants[platform]);
    if(Object.keys(variants).length && looksLikeNewPost(text) && missingPlatforms.length && /\b(version|also|add|across|for)\b/i.test(text)){
      const result=await api("/api/ai/generate",{method:"POST",headers,body:JSON.stringify({brief:lastBrief||text,instruction:text,platforms:missingPlatforms,thread_length:+document.getElementById("threadLength").value,link_url:document.getElementById("linkUrl").value,draft_id:currentDraftId})});
      variants=result.variants;currentDraftId=result.draft_id;currentPlatform=missingPlatforms[0];setAutosaveStatus("Saved"); removeThinking(); addAssistantMessage(`I added ${missingPlatforms.map(platformName).join(" and ")} to this post.`,draftWorkspace()); return;
    }
    if(Object.keys(variants).length && !looksLikeNewPost(text)){
      const target=platformMention(text)||currentPlatform;
      const result=await api("/api/ai/rewrite",{method:"POST",headers,body:JSON.stringify({platform:target,posts:variants[target].posts,action:"",instruction:text})});
      variants[target].posts=result.posts;currentPlatform=target;scheduleAutosave();removeThinking();addAssistantMessage(`Done. I updated the ${platformName(target)} version.`,draftWorkspace());return;
    }
    const platforms=requestedPlatforms; if(!platforms.length) throw new Error("Choose at least one social platform."); if(!validateVideoPlatforms(platforms)) throw new Error("Videos can only be used with Instagram and TikTok.");
    const result=await api("/api/ai/generate",{method:"POST",headers,body:JSON.stringify({brief:text,instruction:"",platforms,thread_length:+document.getElementById("threadLength").value,link_url:document.getElementById("linkUrl").value})});
    variants=result.variants;lastBrief=text;currentDraftId=result.draft_id;currentDraftStatus="draft";currentPlatform=platforms[0];setAutosaveStatus("Saved");removeThinking();addAssistantMessage("I made a native version for every selected platform. Switch between them below, then tell me what to change in the chat box.",draftWorkspace());loadHistory();
  }catch(error){removeThinking();addAssistantMessage(error.message||"Something went wrong. Try that again.");}
  finally{busy(button,false);document.getElementById("brief").focus();}
}

function platformMention(text){const lower=text.toLowerCase();if(/\b(insta|instagram)\b/.test(lower)&&variants.instagram)return"instagram";if(/\bfacebook\b/.test(lower)&&variants.facebook)return"facebook";if(/\btiktok\b/.test(lower)&&variants.tiktok)return"tiktok";if(/\b(x|twitter)\b/.test(lower)&&variants.x)return"x";return null;}
function draftWorkspace(){const platforms=Object.keys(variants),missing=["x","instagram","facebook","tiktok"].filter(p=>!variants[p]),locked=["published","scheduled"].includes(currentDraftStatus);return `<section class="inline-draft" data-current-draft><div class="draft-tabs" aria-label="Generated platform versions">${platforms.map(p=>`<button class="draft-tab ${p===currentPlatform?"active":""}" onclick="switchPlatform('${p}')">${platformIcon(p)} ${platformName(p)} <span>Ready</span></button>`).join("")}<span id="autosaveStatus" class="autosave-status">${locked?currentDraftStatus:"Saved"}</span></div><div id="variantEditor">${editorMarkup()}</div>${locked?"":`<div class="draft-actions"><span class="action-label">Refine in chat</span><div class="refine-chips"><button onclick="promptComposer('Make the ${platformName(currentPlatform)} version shorter')">Shorter</button><button onclick="promptComposer('Make the ${platformName(currentPlatform)} version more serious')">More serious</button><button onclick="promptComposer('Make the ${platformName(currentPlatform)} version more playful')">More playful</button><button onclick="promptComposer('Make the ${platformName(currentPlatform)} version more data-led')">More data-led</button></div>${missing.length?`<div class="add-platforms"><span>Add another version</span>${missing.map(p=>`<button onclick="promptComposer('Add a ${platformName(p)} version of this post')">${platformIcon(p)} ${platformName(p)}</button>`).join("")}</div>`:""}</div>`}<div class="publish-row"><span>${platforms.length} platform${platforms.length===1?"":"s"} ${locked?currentDraftStatus:"ready"}</span><div><a class="text-button" href="/drafts">All drafts</a>${locked?"":`<button class="button ghost" onclick="promptComposer('Suggest the best time to schedule these posts')">Schedule</button><button class="button primary" onclick="requestPublishConfirmation('publish')">Publish</button>`}</div></div></section>`;}
function editorMarkup(){const posts=(variants[currentPlatform]||{}).posts||[],locked=["published","scheduled"].includes(currentDraftStatus),rule=currentPlatform==="x"?"280 characters max per post":(["instagram","tiktok"].includes(currentPlatform)?"Media required to publish":"Ready to publish");return `<div class="draft-platform-head"><b>${platformIcon(currentPlatform)} ${platformName(currentPlatform)}</b><span>${rule}</span></div>${posts.map((post,index)=>`<label class="post-copy"><span>${posts.length>1?`Post ${index+1}`:"Draft"}</span><textarea rows="${posts.length>1?4:6}" ${locked?"readonly":""} oninput="updateDraftPost('${currentPlatform}',${index},this.value)">${esc(post)}</textarea><small>${currentPlatform==="x"?`<b data-character-count>${post.length}</b> / 280`:"Auto-saved"}</small></label>`).join("")}`;}
function refreshDraft(){const card=document.querySelector("[data-current-draft]");if(!card)return;card.outerHTML=draftWorkspace();scrollChat();}
function switchPlatform(platform){currentPlatform=platform;refreshDraft();}
function updateDraftPost(platform,index,value){if(!variants[platform])return;variants[platform].posts[index]=value;const counter=document.querySelector('[data-character-count]');if(counter)counter.textContent=value.length;scheduleAutosave();}
function setAutosaveStatus(text){const status=document.getElementById("autosaveStatus");if(status)status.textContent=text;}
function draftPayload(){return{brief:lastBrief,instruction:"",platforms:Object.keys(variants),variants,thread_length:+document.getElementById("threadLength").value};}
function scheduleAutosave(){if(!currentDraftId||["published","scheduled"].includes(currentDraftStatus))return;setAutosaveStatus("Saving…");clearTimeout(autosaveTimer);autosaveTimer=setTimeout(saveDraftNow,650);}
async function saveDraftNow(){if(!currentDraftId||!Object.keys(variants).length||["published","scheduled"].includes(currentDraftStatus))return;clearTimeout(autosaveTimer);autosaveInFlight=api(`/api/drafts/${currentDraftId}`,{method:"PATCH",headers,body:JSON.stringify(draftPayload())});try{await autosaveInFlight;setAutosaveStatus("Saved");loadHistory();}catch(error){setAutosaveStatus("Save failed");throw error;}finally{autosaveInFlight=null;}}
function saveEditors(){return saveDraftNow();}
function updateCount(){}
function promptComposer(text){const input=document.getElementById("brief");input.value=text;input.focus();input.setSelectionRange(text.length,text.length);}

async function uploadMedia(){const files=document.getElementById("mediaInput").files;if(!files.length)return;const videos=[...files].filter(f=>f.type.startsWith("video/"));const status=document.getElementById("mediaStatus");if(videos.length&&(videos.length>1||files.length>1)){status.textContent="Add one video at a time, without images.";return;}if(videos.length)uploadedVideoDuration=await readVideoDuration(videos[0]);const form=new FormData();[...files].forEach(f=>form.append("files",f));status.textContent="Uploading…";try{const result=await api("/api/media",{method:"POST",headers:{"X-Zova-Request":"1"},body:form});uploadedMediaIds=result.assets.map(a=>a.id);uploadedMedia=result.assets;uploadedMediaKind=result.assets.some(a=>a.kind==="video")?"video":"image";if(uploadedMediaKind==="video"){document.getElementById("px").checked=false;document.getElementById("pfb").checked=false;}document.getElementById("attachmentTray").classList.remove("hidden");document.getElementById("attachmentTray").innerHTML=result.assets.map(a=>`<span>${a.kind==="video"?"Video":"Image"} · ${esc(a.filename)}</span>`).join("");status.textContent=uploadedMediaKind==="video"?"Video attached · Instagram and TikTok only":`${result.assets.length} image${result.assets.length===1?"":"s"} attached`;}catch(error){status.textContent=error.message;}}
function readVideoDuration(file){return new Promise(resolve=>{const video=document.createElement("video"),url=URL.createObjectURL(file);video.preload="metadata";video.onloadedmetadata=()=>{const d=Number(video.duration||0);URL.revokeObjectURL(url);resolve(d);};video.onerror=()=>{URL.revokeObjectURL(url);resolve(0);};video.src=url;});}
function validateVideoPlatforms(platforms){return uploadedMediaKind!=="video"||platforms.every(p=>["instagram","tiktok"].includes(p));}

/* Conversational publish flow: the composer is the only text/date input surface. */
async function publishSelected(){await requestPublishConfirmation("publish");}
async function scheduleSelected(){await suggestSchedule();}
async function requestPublishConfirmation(mode,scheduledLocal=null){
  const platforms=Object.keys(variants); if(!platforms.length)return;
  if(!validateVideoPlatforms(platforms)){addAssistantMessage("Videos can only be published to Instagram and TikTok.");return;}
  try{await saveDraftNow();}catch(error){addAssistantMessage("I could not save this draft. Try again before publishing.");return;}
  addThinking();
  try{
    const result=await api("/api/publish-context",{method:"POST",headers,body:JSON.stringify({platforms,variants})});
    reviewContexts=result.platforms; removeThinking();
    const blocked=platforms.filter(platform=>reviewContexts[platform]?.error);
    if(blocked.length){addAssistantMessage(`Connect ${blocked.map(platformName).join(" and ")} before publishing.`,draftWorkspace());return;}
    reviewMode=mode; pendingSchedule=scheduledLocal;
    const timing=mode==="schedule"?` for ${new Date(scheduledLocal).toLocaleString()}`:" now";
    addAssistantMessage(`Everything is ready to publish${timing}.`,confirmationCard(platforms,mode));
  }catch(error){removeThinking();addAssistantMessage(error.message);}
}
function confirmationCard(platforms,mode){return `<section class="chat-confirmation"><div class="confirmation-platforms">${platforms.map(platform=>`<span>${platformIcon(platform)} ${platformName(platform)}</span>`).join("")}</div><p>${mode==="schedule"?`Schedule all ${platforms.length} versions for <b>${esc(new Date(pendingSchedule).toLocaleString())}</b>?`:`Publish all ${platforms.length} versions to the connected accounts?`}</p><div><button class="button ghost" onclick="promptComposer('I want to make another change')">Make a change</button><button class="button primary" onclick="confirmChatPublish(this)">${mode==="schedule"?"Confirm schedule":"Confirm publish"}</button></div></section>`;}
function chatPublishOptions(platforms){const options={};if(platforms.includes("tiktok")){const context=reviewContexts.tiktok||{},privacy=(context.privacy_options||[]);options.tiktok={privacy_level:privacy.includes("SELF_ONLY")?"SELF_ONLY":privacy[0],allow_comment:!context.comment_disabled,allow_duet:!context.duet_disabled,allow_stitch:!context.stitch_disabled,your_brand:false,brand_content:false,video_duration_sec:uploadedVideoDuration};}return options;}
async function confirmChatPublish(button){const platforms=Object.keys(variants),payload={draft_id:currentDraftId,platforms,variants,media_asset_ids:uploadedMediaIds,link_url:document.getElementById("linkUrl").value,publish_options:chatPublishOptions(platforms)};if(reviewMode==="schedule")payload.scheduled_local=pendingSchedule;busy(button,true,reviewMode==="schedule"?"Scheduling…":"Publishing…");try{await saveDraftNow();const result=await api(reviewMode==="schedule"?"/api/schedule":"/api/publish",{method:"POST",headers,body:JSON.stringify(payload)});currentDraftStatus=result.draft_status||currentDraftStatus;button.closest(".chat-confirmation")?.remove();addAssistantMessage(result.summary);loadSidebar();loadHistory();}catch(error){addAssistantMessage(error.message);}finally{busy(button,false);}}
async function suggestSchedule(context=""){const platforms=Object.keys(variants);addThinking();try{const result=await api("/api/ai/schedule",{method:"POST",headers,body:JSON.stringify({platforms,context:context||lastBrief||conversation.at(-2)?.content||""})});removeThinking();const seen=new Set(),suggestions=[];for(const platform of platforms){for(const item of (result.suggestions[platform]||[]).slice(0,2)){if(!seen.has(item.local_time)){seen.add(item.local_time);suggestions.push(item);}}}addAssistantMessage("Here are the strongest times. Choose one, or tell me a different time in the chat box.",`<div class="schedule-chat-options">${suggestions.slice(0,4).map(item=>`<button onclick="useTime('${item.local_time}','${esc(item.label)}')">${esc(item.label)}</button>`).join("")}</div>`);}catch(error){removeThinking();addAssistantMessage(error.message);}}
function useTime(value,label){addUserMessage(`Schedule these posts for ${label}`);requestPublishConfirmation("schedule",value);}

async function loadSidebar(){try{const data=await api("/api/analytics"),s=data._summary||{};const connected=Object.entries(data).filter(([k,v])=>k!=="_summary"&&v.connected);document.getElementById("connectionPulse").innerHTML=`<i></i>${connected.length?`${connected.length} social${connected.length===1?"":"s"} connected`:"Connect your socials"}`;document.getElementById("analytics").innerHTML=`<div class="pulse-metrics"><div><strong>${Number(s.impressions||0).toLocaleString()}</strong><span>Impressions</span></div><div><strong>${Number(s.likes||0).toLocaleString()}</strong><span>Likes</span></div><div><strong>${Number(s.comments||0).toLocaleString()}</strong><span>Comments</span></div><div><strong>${Number(s.shares||0).toLocaleString()}</strong><span>Shares</span></div></div><a class="analytics-link" href="/analytics">Open full analytics →</a><button class="ask-data" onclick="askQuestion('What is working across my accounts?')">Ask in chat</button>`;}catch(error){document.getElementById("analytics").innerHTML=`<div class="tiny-error">${esc(error.message)}</div>`;}try{const feed=await api("/api/recent-posts"),rows=feed.posts||[];document.getElementById("recentActivity").innerHTML=rows.length?rows.slice(0,4).map(row=>`<a class="recent-post" target="_blank" rel="noopener" href="${esc(row.url||"#")}">${row.image_url?`<img src="${esc(row.image_url)}" alt="">`:`<span class="post-platform-art">${platformIcon(row.platform)}</span>`}<div class="recent-post-copy"><div class="recent-post-platform">${platformIcon(row.platform)}<b>${platformName(row.platform)}</b></div><p>${esc(row.text||"Media post").slice(0,90)}</p><div class="post-metrics"><span>♥ ${Number(row.likes||0).toLocaleString()}</span><span>◯ ${Number(row.comments||0).toLocaleString()}</span><span>↗ ${Number(row.shares||0).toLocaleString()}</span></div></div></a>`).join(""):'<div class="empty-feed">Your recent posts will appear here.</div>';}catch(error){document.getElementById("recentActivity").innerHTML=`<div class="tiny-error">${esc(error.message)}</div>`;}}
async function loadHistory(){try{const rows=await api("/api/drafts");document.getElementById("draftHistory").innerHTML=rows.length?rows.slice(0,6).map(row=>`<a class="chat-history-row" href="/studio?draft=${row.id}"><span>${row.platforms.map(platformName).join(" + ")||"Idea"}</span><b>${esc(row.brief||"Untitled draft").slice(0,54)}</b><small>${new Date(row.updated_at||row.created_at).toLocaleDateString()}</small></a>`).join("")+`<a class="history-all" href="/drafts">View all drafts →</a>`:'<div class="empty-feed">Your drafts will appear here.</div>';}catch{}}
function askQuestion(text){document.getElementById("brief").value=text;sendMessage();}
function useStarter(button){const text=button.textContent;if(text==="Create posts from an idea"){document.getElementById("brief").placeholder="Tell Zova the idea, source or announcement…";document.getElementById("brief").focus();return;}askQuestion(text);}
async function loadRequestedDraft(){const id=new URLSearchParams(location.search).get("draft");if(!id)return;try{const row=await api(`/api/drafts/${encodeURIComponent(id)}`);variants=row.variants||{};currentDraftId=row.id;currentDraftStatus=row.status||"draft";lastBrief=row.brief||"";currentPlatform=row.platforms?.find(platform=>variants[platform])||Object.keys(variants)[0]||"x";document.querySelectorAll(".platform-check input").forEach(input=>input.checked=Boolean(variants[input.value]));document.getElementById("threadLength").value=String(row.thread_length||1);document.getElementById("chatFeed").innerHTML="";addAssistantMessage(currentDraftStatus==="draft"?"Your saved draft is ready. Continue editing here or tell me what to change.":`This item is ${currentDraftStatus}. You can review the platform versions below.`,draftWorkspace());}catch(error){addAssistantMessage(error.message);}}
function newConversation(){saveDraftNow().catch(()=>{});history.replaceState({},"","/studio");variants={};currentDraftId=null;currentDraftStatus="draft";conversation=[];lastBrief="";pendingSchedule=null;uploadedMediaIds=[];uploadedMedia=[];uploadedMediaKind=null;document.getElementById("chatFeed").innerHTML='<article class="chat-message assistant-message welcome-message"><div class="assistant-avatar">Z</div><div class="message-content"><div class="message-name">Zova</div><h2>Fresh chat. What are we working on?</h2><p>Ask about performance or describe the next post.</p></div></article>';document.getElementById("brief").focus();}

document.getElementById("mediaInput").addEventListener("change",uploadMedia);
document.getElementById("brief").addEventListener("keydown",event=>{if(event.key==="Enter"&&!event.shiftKey){event.preventDefault();sendMessage();}});
document.getElementById("threadLength").addEventListener("change",scheduleAutosave);
window.addEventListener("beforeunload",()=>{if(autosaveTimer)saveDraftNow().catch(()=>{});});
loadSidebar();loadHistory();loadRequestedDraft();document.getElementById("brief").focus();
