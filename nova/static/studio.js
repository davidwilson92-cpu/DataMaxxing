let variants = {};
let currentPlatform = "x";
let currentDraftId = null;
let uploadedMediaIds = [];
let uploadedMediaKind = null;
const headers = {"Content-Type": "application/json", "X-Zova-Request": "1"};

const selectedPlatforms = () => [...document.querySelectorAll(".platform-check input:checked")].map(input => input.value);
const esc = value => String(value || "").replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[char]));
const platformName = value => value === "x" ? "X" : value.charAt(0).toUpperCase() + value.slice(1);

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
  const form = new FormData();
  [...files].forEach(file => form.append("files", file));
  status.textContent = "Uploading...";
  try {
    const result = await api("/api/media", {method:"POST", headers:{"X-Zova-Request":"1"}, body:form});
    if (result.assets.some(asset => asset.kind === "video")) {
      uploadedMediaIds = result.assets.map(asset => asset.id);
      uploadedMediaKind = "video";
      ["px", "pfb"].forEach(id => { document.getElementById(id).checked = false; });
      status.textContent = "1 video attached · Instagram and TikTok only";
    } else {
      if (uploadedMediaKind === "video") uploadedMediaIds = [];
      uploadedMediaIds.push(...result.assets.map(asset => asset.id));
      uploadedMediaKind = "image";
      status.textContent = `${uploadedMediaIds.length} image${uploadedMediaIds.length === 1 ? "" : "s"} attached`;
    }
  } catch (error) { status.textContent = error.message; }
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
  document.getElementById("platformTabs").innerHTML = Object.keys(variants).map(platform => `<button class="tab ${platform === currentPlatform ? "active" : ""}" onclick="switchPlatform('${platform}')">${platformName(platform)}</button>`).join("");
  renderEditor();
}

function switchPlatform(platform) { saveEditor(); currentPlatform = platform; renderDrafts(); }
function saveEditor() { const boxes = [...document.querySelectorAll("#variantEditor textarea")]; if (boxes.length && variants[currentPlatform]) variants[currentPlatform].posts = boxes.map(box => box.value); }
function updateCount(element) { if (currentPlatform === "x") element.parentNode.querySelector("small").textContent = `${element.value.length} / 280 characters`; }

function renderEditor() {
  const posts = (variants[currentPlatform] || {}).posts || [];
  const rule = currentPlatform === "x" ? "280 characters max per post" : (["instagram","tiktok"].includes(currentPlatform) ? "Visual media required to publish" : "Platform-native version");
  document.getElementById("variantEditor").innerHTML = `<div class="platform-rule"><b>${platformName(currentPlatform)}</b><span>${rule}</span></div>` + posts.map((post,index) => `<div class="post-editor"><label>${posts.length > 1 ? `Post ${index + 1}` : "Draft"}</label><textarea rows="${posts.length > 1 ? 4 : 7}" oninput="updateCount(this)">${esc(post)}</textarea><small>${currentPlatform === "x" ? `${post.length} / 280 characters` : ""}</small></div>`).join("");
}

async function requestRewrite(action = "", instruction = "") { saveEditor(); try { const result = await api("/api/ai/rewrite", {method:"POST",headers,body:JSON.stringify({platform:currentPlatform,posts:variants[currentPlatform].posts,action,instruction})}); variants[currentPlatform].posts = result.posts; renderEditor(); } catch (error) { alert(error.message); } }
async function rewrite(action) { return requestRewrite(action); }
async function refineCustom() { const input = document.getElementById("refineInstruction"); const instruction = input.value.trim(); if (!instruction) return input.focus(); await requestRewrite("", instruction); input.value = ""; }
async function previewCurrent() { saveEditor(); const platforms = selectedPlatforms().filter(p => variants[p]); try { const result = await api("/api/preview", {method:"POST",headers,body:JSON.stringify({platforms,variants})}); document.getElementById("previewResult").textContent = result.summary; } catch (error) { alert(error.message); } }

async function publishSelected() {
  saveEditor(); const platforms = selectedPlatforms().filter(p => variants[p]);
  if (!platforms.length) return alert("Choose a generated platform draft.");
  if (!validateVideoPlatforms(platforms)) return;
  if (!confirm(`Publish now to ${platforms.map(platformName).join(", ")}?`)) return;
  try { const result = await api("/api/publish", {method:"POST",headers,body:JSON.stringify({draft_id:currentDraftId,platforms,variants,media_asset_ids:uploadedMediaIds,link_url:document.getElementById("linkUrl").value})}); alert(result.summary); loadSidebar(); loadHistory(); } catch (error) { alert(error.message); }
}

async function scheduleSelected() {
  saveEditor(); const scheduled = document.getElementById("scheduleAt").value;
  if (!scheduled) return alert("Choose a scheduled date and time.");
  const platforms = selectedPlatforms().filter(p => variants[p]);
  if (!validateVideoPlatforms(platforms)) return;
  try { const result = await api("/api/schedule", {method:"POST",headers,body:JSON.stringify({draft_id:currentDraftId,platforms,variants,media_asset_ids:uploadedMediaIds,link_url:document.getElementById("linkUrl").value,scheduled_local:scheduled})}); alert(result.summary); loadSidebar(); } catch (error) { alert(error.message); }
}

async function suggestSchedule() {
  const platforms = selectedPlatforms().filter(p => variants[p]);
  try { const result = await api("/api/ai/schedule", {method:"POST",headers,body:JSON.stringify({platforms,context:document.getElementById("brief").value})}); let html = ""; for (const platform of platforms) { html += `<b>${platformName(platform)}</b>`; (result.suggestions[platform] || []).forEach(item => html += `<button onclick="useTime('${item.local_time}')">${esc(item.label)} · ${esc(item.local_time.replace("T"," "))}</button>`); } document.getElementById("scheduleSuggestions").innerHTML = html; } catch (error) { alert(error.message); }
}

function useTime(value) { document.getElementById("scheduleAt").value = value; }
function clearComposer() { document.getElementById("brief").value = ""; document.getElementById("instruction").value = ""; document.getElementById("linkUrl").value = ""; document.getElementById("mediaInput").value = ""; variants = {}; currentDraftId = null; uploadedMediaIds = []; uploadedMediaKind = null; document.getElementById("mediaStatus").textContent = ""; document.getElementById("draftArea").classList.add("hidden"); }

async function loadSidebar() {
  try {
    const data = await api("/api/analytics"); const summary = data._summary || {};
    const connected = Object.entries(data).filter(([key,value]) => key !== "_summary" && value.connected);
    const score = value => (value.likes || value.reactions || 0) + (value.comments || value.replies || 0) + (value.shares || value.reposts || 0);
    const trending = connected.length ? platformName(connected.sort((a,b) => score(b[1]) - score(a[1]))[0][0]) : "No signal yet";
    document.getElementById("analytics").innerHTML = `<div class="analytics-period">LAST 7 DAYS</div><div class="analytics-summary"><div><strong>${Number(summary.impressions || 0).toLocaleString()}</strong><span>Impressions</span></div><div><strong>${Number(summary.likes || 0).toLocaleString()}</strong><span>Likes</span></div><div><strong>${Number(summary.comments || 0).toLocaleString()}</strong><span>Comments</span></div><div><strong>${Number(summary.shares || 0).toLocaleString()}</strong><span>Shares / reposts</span></div><div><strong>${Number(summary.followers || 0).toLocaleString()}</strong><span>Followers</span></div><div><strong>${esc(trending)}</strong><span>Trending account</span></div></div><a class="analytics-link" href="/account#socials">Manage connected accounts →</a>`;
  } catch (error) { document.getElementById("analytics").innerHTML = `<div class="tiny-error">${esc(error.message)}</div>`; }
  try { const rows = await api("/api/activity"); document.getElementById("recentActivity").innerHTML = rows.length ? rows.map(row => `<div class="activity-row"><span class="platform-dot ${row.platform}"></span><div><b>${platformName(row.platform)} · ${esc(row.status)}</b><p>${esc(row.text).slice(0,100)}</p><small>${new Date(row.created_at).toLocaleString()}</small></div>${row.url ? `<a target="_blank" href="${esc(row.url)}">↗</a>` : ""}</div>`).join("") : '<div class="muted">No activity yet.</div>'; } catch {}
}

async function loadHistory() {
  try { const rows = await api("/api/drafts"); document.getElementById("draftHistory").innerHTML = rows.length ? `<div class="history-head"><span>Created</span><span>Platforms</span><span>Status</span><span>Brief</span><span>Links</span></div>` + rows.map(row => `<div class="history-row"><span>${new Date(row.created_at).toLocaleDateString()}</span><span>${esc(row.platforms.map(platformName).join(", "))}</span><span class="status ${esc(row.status)}">${esc(row.status)}</span><span>${esc(row.brief).slice(0,90)}</span><span>${(row.links || []).map(link => `<a target="_blank" href="${esc(link.url)}">${platformName(link.platform)} ↗</a>`).join(" ")}</span></div>`).join("") : '<div class="muted">Your generated drafts will appear here.</div>'; } catch {}
}

document.getElementById("mediaInput").addEventListener("change", uploadMedia);
loadSidebar();
loadHistory();
