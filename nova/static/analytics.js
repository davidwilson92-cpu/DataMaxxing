const analyticsEsc=value=>String(value??"").replace(/[&<>"']/g,char=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[char]));
const analyticsNumber=value=>Number(value||0).toLocaleString();
const analyticsPlatform=value=>value==="x"?"X":value.charAt(0).toUpperCase()+value.slice(1);
const analyticsIcon=platform=>platform==="x"?'𝕏':platform==="instagram"?'IG':platform==="facebook"?'f':'♪';

async function analyticsApi(url,options={}){const response=await fetch(url,options);let data;try{data=await response.json();}catch{data={detail:"Zova could not read that response."};}if(!response.ok)throw new Error(data.detail||"Request failed");return data;}

function renderKpis(summary){const metrics=[
  ["Impressions",summary.impressions,"Available views and impressions"],
  ["Engagements",summary.engagements,"Likes, comments and shares"],
  ["Engagement rate",summary.engagement_rate==null?"—":`${summary.engagement_rate}%`,"Engagements divided by impressions"],
  ["Followers",summary.followers,"Across connected accounts"],
  ["Posts",summary.posts,"Posts represented in this view"]
];document.getElementById("analyticsKpis").innerHTML=metrics.map(([label,value,note],index)=>`<article class="analytics-kpi ${index===0?"primary":""}"><span>${label}</span><strong>${typeof value==="number"?analyticsNumber(value):value}</strong><small>${note}</small></article>`).join("");}

function renderPlatforms(platforms){const connected=Object.entries(platforms).filter(([,value])=>value.connected);const max=Math.max(1,...connected.map(([,value])=>Number(value.engagements||0)));document.getElementById("platformPerformance").innerHTML=connected.length?connected.map(([name,value])=>`<article class="platform-performance-row"><div class="analytics-platform-mark ${name}">${analyticsIcon(name)}</div><div class="platform-performance-main"><div><strong>${analyticsPlatform(name)}</strong><span>${analyticsEsc(value.account||"Connected")}</span></div><div class="performance-bar"><i style="width:${Math.max(3,Number(value.engagements||0)*100/max)}%"></i></div><dl><div><dt>Impressions</dt><dd>${analyticsNumber(value.impressions)}</dd></div><div><dt>Engagements</dt><dd>${analyticsNumber(value.engagements)}</dd></div><div><dt>Rate</dt><dd>${value.engagement_rate==null?"—":`${value.engagement_rate}%`}</dd></div><div><dt>Followers</dt><dd>${analyticsNumber(value.followers)}</dd></div></dl>${value.error?`<small class="metric-note">Some metrics are temporarily unavailable.</small>`:""}</div></article>`).join(""):'<div class="analytics-empty">Connect a social account to create your cross-platform view. <a href="/account#socials">Manage accounts →</a></div>';}

function renderRecommendations(items){document.getElementById("recommendations").innerHTML=items.length?items.map((item,index)=>`<article class="recommendation-item"><span>0${index+1}</span><div><h3>${analyticsEsc(item.title)}</h3><p>${analyticsEsc(item.detail)}</p></div></article>`).join(""):'<div class="analytics-empty">Zova needs more account activity before making a useful recommendation.</div>';}

function renderPosts(posts){document.getElementById("topPosts").innerHTML=posts.length?posts.map(post=>`<a class="analytics-post" href="${analyticsEsc(post.url||"#")}" ${post.url?'target="_blank" rel="noopener"':''}>${post.image_url?`<img src="${analyticsEsc(post.image_url)}" alt="">`:`<span class="analytics-post-art ${post.platform}">${analyticsIcon(post.platform)}</span>`}<div><span class="post-channel">${analyticsPlatform(post.platform)}</span><p>${analyticsEsc(post.text||"Media post").slice(0,170)}</p><dl><div><dt>Likes</dt><dd>${analyticsNumber(post.likes)}</dd></div><div><dt>Comments</dt><dd>${analyticsNumber(post.comments)}</dd></div><div><dt>Shares</dt><dd>${analyticsNumber(post.shares)}</dd></div><div><dt>Views</dt><dd>${analyticsNumber(post.views)}</dd></div></dl></div></a>`).join(""):'<div class="analytics-empty">Recent posts will appear after connected platforms return account activity.</div>';}

async function loadAnalytics(){try{const data=await analyticsApi("/api/analytics/dashboard");renderKpis(data.summary||{});renderPlatforms(data.platforms||{});renderRecommendations(data.recommendations||[]);renderPosts(data.top_posts||[]);}catch(error){document.getElementById("analyticsKpis").innerHTML=`<div class="analytics-error">${analyticsEsc(error.message)}</div>`;}}

async function askAnalytics(question){const answer=document.getElementById("analyticsAnswer"),button=document.querySelector("#analyticsQuestion button");answer.hidden=false;answer.innerHTML='<span class="analysis-thinking">Analysing your account signals…</span>';button.disabled=true;try{const result=await analyticsApi("/api/insights",{method:"POST",headers:{"Content-Type":"application/json","X-Zova-Request":"1"},body:JSON.stringify({question})});answer.innerHTML=`<div class="eyebrow">ZOVA ANSWER</div><p>${analyticsEsc(result.answer)}</p>`;}catch(error){answer.textContent=error.message;}finally{button.disabled=false;}}

document.getElementById("analyticsQuestion").addEventListener("submit",event=>{event.preventDefault();const field=document.getElementById("analyticsQuestionText"),question=field.value.trim();if(question)askAnalytics(question);});
document.querySelectorAll(".analytics-prompts button").forEach(button=>button.addEventListener("click",()=>{document.getElementById("analyticsQuestionText").value=button.textContent;askAnalytics(button.textContent);}));
loadAnalytics();
