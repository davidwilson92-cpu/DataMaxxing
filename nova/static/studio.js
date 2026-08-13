let variants = {};
let currentPlatform = "x";
let currentDraftId = null;
let uploadedMediaIds = [];
let uploadedMediaKind = null;
let uploadedMedia = [];
let uploadedVideoDuration = 0;
let reviewMode = "publish";
let reviewContexts = {};
const headers = {"Content-Type": "application/json", "X-Zova-Request": "1"};

const selectedPlatforms = () => [...document.querySelectorAll(".platform-check input:checked")].map(input => input.value);
const esc = value => String(value || "").replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[char]));
const platformName = value => value === "x" ? "X" : value.charAt(0).toUpperCase() + value.slice(1);
const platformIcon = platform => platform === "x" ? '<svg class="inline-social-icon x" viewBox="0 0 24 24" aria-hidden="true"><path d="M18.24 2.25h3.31l-7.23 8.26 8.5 11.24h-6.66l-5.21-6.82-5.97 6.82H1.67l7.74-8.84L1.25 2.25h6.83l4.71 6.23 5.45-6.23Zm-1.16 17.52h1.83L7.08 4.13H5.12l11.96 15.64Z"/></svg>' : platform === "instagram" ? '<span class="inline-social-icon instagram">IG</span>' : platform === "facebook" ? '<span class="inline-social-icon facebook">f</span>' : '<span class="inline-social-icon tiktok">♪</span>';

async function api(url, options = {}) {
  const response = await fetch(url, options);
  let payload;
  try { payload = await response.json(); } catch { payload = {detail: await response.text()}; }
  if (!response.ok) throw new Error(payload.detail || "Request failed");
  return payload;
}

function busy(button, active, label) {
  button.disabled = active;
  if (active) { button.dataset.old = button.textContent; button.textContent = label; }
  else button.textContent = button.dataset.old || button.textContent;
}

async function uploadMedia() {
  const files = document.getElementById("mediaInput").files;
  if (!files.length) return;
  const videos = [...files].filter(file => file.type.startsWith("video/"));
  const status = document.getElementById("mediaStatus");
  if (videos.length && (videos.length > 1 || files.length > 1)) {
    status.textContent = "Add one video at a time, without images.";
    return;
  }
  if (videos.length) uploadedVideoDuration = await readVideoDuration(videos[0]);
  const form = new FormData();
  [...files].forEach(file => form.append("files", file));
  status.textContent = "Uploading...";
  try {
    const result = await api("/api/media", {method:"POST", headers:{"X-Zova-Request":"1"}, body:form});
    if (result.assets.some(asset => asset.kind === "video")) {
      uploadedMediaIds = result.assets.map(asset => asset.id);
      uploadedMedia = result.assets;
      uploadedMediaKind = "video";
      ["px", "pfb"].forEach(id => { document.getElementById(id).checked = false; });
      status.textContent = "1 video attached · Instagram and TikTok only";
    } else {
      if (uploadedMediaKind === "video") uploadedMediaIds = [];
      uploadedMediaIds.push(...result.assets.map(asset => asset.id));
      if (uploadedMediaKind === "video") uploadedMedia = [];
      uploadedMedia.push(...result.assets);
      uploadedMediaKind = "image";
      status.textContent = `${uploadedMediaIds.length} image${uploadedMediaIds.length === 1 ? "" : "s"} attached`;
    }
  } catch (error) { status.textContent = error.message; }
}

function readVideoDuration(file) {
  return new Promise(resolve => {
    const video = document.createElement("video"); const url = URL.createObjectURL(file);
    video.preload = "metadata";
    video.onloadedmetadata = () => { const duration = Number(video.duration || 0); URL.revokeObjectURL(url); resolve(duration); };
    video.onerror = () => { URL.revokeObjectURL(url); resolve(0); };
    video.src = url;
  });
}

function validateVideoPlatforms(platforms) {
  if (uploadedMediaKind !== "video") return true;
  const unsupported = platforms.filter(platform => !["instagram", "tiktok"].includes(platform));
  if (!unsupported.length) return true;
  alert(`Videos can only be used with Instagram and TikTok. Remove ${unsupported.map(platformName).join(", ")}.`);
  return false;
}

async function generateDraft() {
  const button = document.getElementById("generateBtn");
  const platforms = selectedPlatforms();
  if (!platforms.length) return alert("Choose at least one social platform.");
  if (!validateVideoPlatforms(platforms)) return;
  busy(button, true, "Generating...");
  try {
    const result = await api("/api/ai/generate", {method:"POST", headers, body:JSON.stringify({brief:document.getElementById("brief").value,instruction:document.getElementById("instruction").value,platforms,thread_length:+document.getElementById("threadLength").value,link_url:document.getElementById("linkUrl").value})});
    variants = result.variants; currentDraftId = result.draft_id; currentPlatform = platforms[0];
    renderDrafts(); loadHistory();
  } catch (error) { alert(error.message); } finally { busy(button, false); }
}

function renderDrafts() {
  document.getElementById("draftArea").classList.remove("hidden");
  document.getElementById("platformTabs").innerHTML = Object.keys(variants).map(platform => `<button class="tab ${platform === currentPlatform ? "active" : ""}" onclick="switchPlatform('${platform}')">${platformIcon(platform)}<span>${platformName(platform)}</span></button>`).join("");
  renderEditor();
}

function switchPlatform(platform) { saveEditor(); currentPlatform = platform; renderDrafts(); }
function saveEditor() { const boxes = [...document.querySelectorAll("#variantEditor textarea")]; if (boxes.length && variants[currentPlatform]) variants[currentPlatform].posts = boxes.map(box => box.value); }
function updateCount(element) { if (currentPlatform === "x") element.parentNode.querySelector("small").textContent = `${element.value.length} / 280 characters`; }

function renderEditor() {
  const posts = (variants[currentPlatform] || {}).posts || [];
  const rule = currentPlatform === "x" ? "280 characters max per post" : (["instagram","tiktok"].includes(currentPlatform) ? "Visual media required to publish" : "Platform-native version");
  document.getElementById("variantEditor").innerHTML = `<div class="platform-rule"><b>${platformIcon(currentPlatform)}${platformName(currentPlatform)}</b><span>${rule}</span></div>` + posts.map((post,index) => `<div class="post-editor"><label>${posts.length > 1 ? `Post ${index + 1}` : "Draft"}</label><textarea rows="${posts.length > 1 ? 3 : 4}" oninput="updateCount(this)">${esc(post)}</textarea><small>${currentPlatform === "x" ? `${post.length} / 280 characters` : ""}</small></div>`).join("");
}

async function requestRewrite(action = "", instruction = "") { saveEditor(); try { const result = await api("/api/ai/rewrite", {method:"POST",headers,body:JSON.stringify({platform:currentPlatform,posts:variants[currentPlatform].posts,action,instruction})}); variants[currentPlatform].posts = result.posts; renderEditor(); } catch (error) { alert(error.message); } }
async function rewrite(action) { return requestRewrite(action); }
async function refineCustom() { const input = document.getElementById("refineInstruction"); const instruction = input.value.trim(); if (!instruction) return input.focus(); await requestRewrite("", instruction); input.value = ""; }
async function previewCurrent() { saveEditor(); const platforms = selectedPlatforms().filter(p => variants[p]); try { const result = await api("/api/preview", {method:"POST",headers,body:JSON.stringify({platforms,variants})}); document.getElementById("previewResult").textContent = result.summary; } catch (error) { alert(error.message); } }

async function publishSelected() { await openPublishReview("publish"); }

async function scheduleSelected() {
  saveEditor(); const scheduled = document.getElementById("scheduleAt").value;
  if (!scheduled) return alert("Choose a scheduled date and time.");
  await openPublishReview("schedule");
}

async function openPublishReview(mode) {
  saveEditor(); const platforms = selectedPlatforms().filter(platform => variants[platform]);
  if (!platforms.length) return alert("Choose a generated platform draft.");
  if (!validateVideoPlatforms(platforms)) return;
  reviewMode = mode; const dialog = document.getElementById("publishReview"); const error = document.getElementById("reviewError");
  error.classList.add("hidden"); document.getElementById("reviewBody").innerHTML = '<div class="review-loading">Checking connected accounts and current platform settings...</div>';
  document.getElementById("reviewTitle").textContent = mode === "schedule" ? "Review scheduled posts" : "Ready to publish?";
  document.getElementById("confirmPublishBtn").textContent = mode === "schedule" ? "Confirm schedule" : "Confirm and publish";
  dialog.showModal();
  try {
    const result = await api("/api/publish-context", {method:"POST",headers,body:JSON.stringify({platforms,variants})}); reviewContexts = result.platforms; renderPublishReview(platforms);
  } catch (problem) { error.textContent = problem.message; error.classList.remove("hidden"); }
}

function renderPublishReview(platforms) {
  const mediaHtml = uploadedMedia.length ? `<div class="review-media"><div class="review-label">ATTACHED MEDIA</div>${uploadedMedia.map(asset => asset.url ? (asset.kind === "video" ? `<video src="${esc(asset.url)}" controls preload="metadata"></video>` : `<img src="${esc(asset.url)}" alt="Attached media preview">`) : `<span>${esc(asset.filename)}</span>`).join("")}</div>` : "";
  const sections = platforms.map(platform => {
    const context = reviewContexts[platform] || {}; const posts = variants[platform].posts || [];
    if (context.error) return `<section class="review-platform blocked"><h3>${platformName(platform)}</h3><div class="alert error">${esc(context.error)} Connect this account before publishing.</div></section>`;
    const account = esc(context.display_name || context.username || "Connected account");
    const editors = posts.map((post,index) => `<label>${posts.length > 1 ? `Post ${index + 1}` : "Caption"}<textarea data-review-platform="${platform}" data-review-index="${index}" rows="${posts.length > 1 ? 3 : 5}">${esc(post)}</textarea></label>`).join("");
    let settings = "";
    if (platform === "tiktok") {
      const privacyOptions = context.privacy_options || [];
      const defaultPrivacy = privacyOptions.includes("SELF_ONLY") ? "SELF_ONLY" : privacyOptions[0];
      const privacy = privacyOptions.map(value => `<option value="${esc(value)}" ${value === defaultPrivacy ? "selected" : ""}>${privacyLabel(value)}</option>`).join("");
      const max = Number(context.max_video_duration_sec || 0); const tooLong = uploadedMediaKind === "video" && max && uploadedVideoDuration > max;
      settings = `<div class="tiktok-settings"><label>Who can view this post?<select id="tiktokPrivacy">${privacy}</select></label>${max ? `<p class="platform-note ${tooLong ? "error-text" : ""}">This account allows videos up to ${max} seconds.${uploadedVideoDuration ? ` Your video is ${Math.ceil(uploadedVideoDuration)} seconds.` : ""}</p>` : ""}<div class="review-switches"><label><input id="allowComment" type="checkbox" ${context.comment_disabled ? "disabled" : "checked"}> Allow comments</label><label><input id="allowDuet" type="checkbox" ${context.duet_disabled ? "disabled" : "checked"}> Allow Duet</label><label><input id="allowStitch" type="checkbox" ${context.stitch_disabled ? "disabled" : "checked"}> Allow Stitch</label></div><div class="commercial-box"><div class="review-label">CONTENT DISCLOSURE</div><label><input id="yourBrand" type="checkbox" onchange="updateTikTokDeclaration()"> This post promotes my own brand</label><label><input id="brandContent" type="checkbox" onchange="updateTikTokDeclaration()"> This post promotes another brand or third party</label><p id="tiktokDeclaration">By posting, you agree to TikTok's Music Usage Confirmation.</p></div>${tooLong ? '<div class="alert error">This video is too long for the connected TikTok account.</div>' : ""}</div>`;
    }
    return `<section class="review-platform" data-platform="${platform}"><div class="review-platform-head"><h3>${platformName(platform)}</h3><span>Publishing to <b>${account}</b>${context.username ? ` · @${esc(context.username).replace(/^@/,"")}` : ""}</span></div>${editors}${settings}</section>`;
  }).join("");
  const timing = reviewMode === "schedule" ? `<div class="review-timing">Scheduled for <b>${esc(document.getElementById("scheduleAt").value.replace("T"," "))}</b></div>` : "";
  document.getElementById("reviewBody").innerHTML = `${timing}${mediaHtml}${sections}<label class="final-consent"><input id="publishConsent" type="checkbox"> I have reviewed this content and authorise Zova to send it to the accounts shown above.</label><p class="processing-note">TikTok and Instagram may take a few minutes to process media after submission. Zova will show the latest status in Activity.</p>`;
}

function privacyLabel(value) { return ({PUBLIC_TO_EVERYONE:"Everyone",MUTUAL_FOLLOW_FRIENDS:"Friends",FOLLOWER_OF_CREATOR:"Followers",SELF_ONLY:"Only me"})[value] || value.replaceAll("_"," ").toLowerCase(); }
function updateTikTokDeclaration() { const branded = document.getElementById("brandContent")?.checked; document.getElementById("tiktokDeclaration").textContent = branded ? "By posting, you agree to TikTok's Branded Content Policy and Music Usage Confirmation." : "By posting, you agree to TikTok's Music Usage Confirmation."; }

function collectPublishOptions(platforms) {
  const options = {};
  if (platforms.includes("tiktok")) options.tiktok = {privacy_level:document.getElementById("tiktokPrivacy").value,allow_comment:document.getElementById("allowComment").checked,allow_duet:document.getElementById("allowDuet").checked,allow_stitch:document.getElementById("allowStitch").checked,your_brand:document.getElementById("yourBrand").checked,brand_content:document.getElementById("brandContent").checked,video_duration_sec:uploadedVideoDuration};
  return options;
}

async function confirmReviewedPublish() {
  const platforms = selectedPlatforms().filter(platform => variants[platform]); const error = document.getElementById("reviewError"); const button = document.getElementById("confirmPublishBtn");
  if (platforms.some(platform => reviewContexts[platform]?.error)) { error.textContent = "Connect every selected account before continuing."; return error.classList.remove("hidden"); }
  if (!document.getElementById("publishConsent")?.checked) { error.textContent = "Confirm that you reviewed and authorised these posts."; return error.classList.remove("hidden"); }
  document.querySelectorAll("[data-review-platform]").forEach(box => { variants[box.dataset.reviewPlatform].posts[Number(box.dataset.reviewIndex)] = box.value; });
  const publishOptions = collectPublishOptions(platforms); const payload = {draft_id:currentDraftId,platforms,variants,media_asset_ids:uploadedMediaIds,link_url:document.getElementById("linkUrl").value,publish_options:publishOptions};
  if (reviewMode === "schedule") payload.scheduled_local = document.getElementById("scheduleAt").value;
  busy(button,true,reviewMode === "schedule" ? "Scheduling..." : "Publishing...");
  try { const result = await api(reviewMode === "schedule" ? "/api/schedule" : "/api/publish",{method:"POST",headers,body:JSON.stringify(payload)}); document.getElementById("publishReview").close(); alert(result.summary + (reviewMode === "publish" && result.results?.tiktok?.pending ? " TikTok is processing the post; follow its status in Activity." : "")); loadSidebar(); loadHistory(); }
  catch (problem) { error.textContent = problem.message; error.classList.remove("hidden"); }
  finally { busy(button,false); }
}

async function suggestSchedule() {
  const platforms = selectedPlatforms().filter(p => variants[p]);
  try { const result = await api("/api/ai/schedule", {method:"POST",headers,body:JSON.stringify({platforms,context:document.getElementById("brief").value})}); let html = ""; for (const platform of platforms) { html += `<b>${platformName(platform)}</b>`; (result.suggestions[platform] || []).forEach(item => html += `<button onclick="useTime('${item.local_time}')">${esc(item.label)} · ${esc(item.local_time.replace("T"," "))}</button>`); } document.getElementById("scheduleSuggestions").innerHTML = html; } catch (error) { alert(error.message); }
}

function useTime(value) { document.getElementById("scheduleAt").value = value; }
function clearComposer() { document.getElementById("brief").value = ""; document.getElementById("instruction").value = ""; document.getElementById("linkUrl").value = ""; document.getElementById("mediaInput").value = ""; variants = {}; currentDraftId = null; uploadedMediaIds = []; uploadedMedia = []; uploadedMediaKind = null; uploadedVideoDuration = 0; document.getElementById("mediaStatus").textContent = ""; document.getElementById("draftArea").classList.add("hidden"); }

async function loadSidebar() {
  try {
    const data = await api("/api/analytics"); const summary = data._summary || {};
    const connected = Object.entries(data).filter(([key,value]) => key !== "_summary" && value.connected);
    const score = value => (value.likes || value.reactions || 0) + (value.comments || value.replies || 0) + (value.shares || value.reposts || 0);
    const trending = connected.length ? platformName(connected.sort((a,b) => score(b[1]) - score(a[1]))[0][0]) : "No signal yet";
    document.getElementById("analytics").innerHTML = `<div class="analytics-period">LAST 7 DAYS</div><div class="analytics-summary"><div><strong>${Number(summary.impressions || 0).toLocaleString()}</strong><span>Impressions</span></div><div><strong>${Number(summary.likes || 0).toLocaleString()}</strong><span>Likes</span></div><div><strong>${Number(summary.comments || 0).toLocaleString()}</strong><span>Comments</span></div><div><strong>${Number(summary.shares || 0).toLocaleString()}</strong><span>Shares / reposts</span></div><div><strong>${Number(summary.followers || 0).toLocaleString()}</strong><span>Followers</span></div><div><strong>${esc(trending)}</strong><span>Trending account</span></div></div><a class="analytics-link" href="/account#socials">Manage connected accounts →</a>`;
  } catch (error) { document.getElementById("analytics").innerHTML = `<div class="tiny-error">${esc(error.message)}</div>`; }
  try {
    const feed = await api("/api/recent-posts"); const rows = feed.posts || [];
    document.getElementById("recentActivity").innerHTML = rows.length ? rows.map(row => `<a class="recent-post" target="_blank" rel="noopener" href="${esc(row.url || "#")}">${row.image_url ? `<img src="${esc(row.image_url)}" alt="" loading="lazy">` : `<span class="post-platform-art ${row.platform}">${platformIcon(row.platform)}</span>`}<div class="recent-post-copy"><div class="recent-post-platform">${platformIcon(row.platform)}<b>${platformName(row.platform)}</b><time>${row.created_at ? new Date(row.created_at).toLocaleDateString() : ""}</time></div><p>${esc(row.text || "Media post").slice(0,115)}</p><div class="post-metrics"><span>♥ ${Number(row.likes || 0).toLocaleString()}</span><span>◯ ${Number(row.comments || 0).toLocaleString()}</span><span>↗ ${Number(row.shares || 0).toLocaleString()}</span>${row.views ? `<span>◉ ${Number(row.views).toLocaleString()}</span>` : ""}</div></div></a>`).join("") : '<div class="empty-feed">Recent posts will appear here once a connected platform makes them available.</div>';
  } catch (error) { document.getElementById("recentActivity").innerHTML = `<div class="tiny-error">${esc(error.message)}</div>`; }
}

async function loadHistory() {
  try { const rows = await api("/api/drafts"); document.getElementById("draftHistory").innerHTML = rows.length ? `<div class="history-head"><span>Created</span><span>Platforms</span><span>Status</span><span>Brief</span><span>Links</span></div>` + rows.map(row => `<div class="history-row"><span>${new Date(row.created_at).toLocaleDateString()}</span><span>${esc(row.platforms.map(platformName).join(", "))}</span><span class="status ${esc(row.status)}">${esc(row.status)}</span><span>${esc(row.brief).slice(0,90)}</span><span>${(row.links || []).map(link => `<a target="_blank" href="${esc(link.url)}">${platformName(link.platform)} ↗</a>`).join(" ")}</span></div>`).join("") : '<div class="muted">Your generated drafts will appear here.</div>'; } catch {}
}

document.getElementById("mediaInput").addEventListener("change", uploadMedia);
loadSidebar();
loadHistory();
