const analyticsEsc=value=>String(value??"").replace(/[&<>"']/g,char=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[char]));
const analyticsNumber=value=>(value==null?"—":Number(value).toLocaleString());
const analyticsPlatform=value=>({x:"X",instagram:"Instagram",facebook:"Facebook",tiktok:"TikTok"}[value]||"Account");
const analyticsIcon = platform => window.zovaPlatformLabel(platform);

async function analyticsApi(url,options={}){const response=await fetch(url,options);let data;try{data=await response.json();}catch{data={detail:"Zova could not read that response."};}if(!response.ok)throw new Error(data.detail||"Request failed");return data;}

function renderKpis(summary){const metrics=[
  ["Views / impressions",summary.impressions,"Available views and impressions"],
  ["Engagements",summary.engagements,"Likes, comments and shares"],
  ["Comments",summary.comments,"Available comments on sampled posts"],
  ["Followers",summary.followers,"Across connected accounts"],
  ["Posts",summary.posts,"Posts represented in this view"]
];const available=metrics.filter(([,value])=>value!=null);document.getElementById("analyticsKpis").innerHTML=available.length?available.map(([label,value,note],index)=>`<article class="analytics-kpi ${index===0?"primary":""}"><span>${label}</span><strong>${value==null?"—":typeof value==="number"?analyticsNumber(value):value}</strong><small>${note}</small></article>`).join(""):'<p class="analytics-empty-summary">Combined totals are incomplete. Available account results are below.</p>';}

function renderPlatforms(platforms){
  const connected=Object.entries(platforms).filter(([,value])=>value.connected);
  document.getElementById('platformPerformance').innerHTML=connected.length?connected.map(([name,value])=>{
    const metrics=[['Views / impressions',value.impressions],['Engagements',value.engagements],['Followers',value.followers]].filter(([,count])=>count!=null);
    return `<article class="platform-performance-row"><div class="analytics-platform-mark ${name}">${analyticsIcon(name)}</div><div class="platform-performance-main"><div><strong>${analyticsPlatform(name)}</strong><span>${analyticsEsc(value.account||'Connected')}</span></div>
    ${metrics.length?`<dl>${metrics.map(([label,count])=>`<div><dt>${label}</dt><dd>${analyticsNumber(count)}</dd></div>`).join('')}</dl>`:'<p class="metric-note">Results are unavailable for this account.</p>'}
    ${value.error&&metrics.length?'<small class="metric-note">Some metrics are unavailable.</small>':''}</div></article>`;
  }).join(''):'<div class="analytics-empty">Connect a social account to see its available results. <a href="/account#socials">Manage accounts →</a></div>';
}

function renderRecommendations(items){document.getElementById("recommendations").innerHTML=items.length?items.map((item,index)=>`<article class="recommendation-item"><span>0${index+1}</span><div><h3>${analyticsEsc(item.title)}</h3><p>${analyticsEsc(item.detail)}</p></div></article>`).join(""):'<div class="analytics-empty">Zova needs more account activity before making a useful recommendation.</div>';}

function analyticsSafeUrl(value) {
  try { const url=new URL(value); return ['http:','https:'].includes(url.protocol)&&!url.username&&!url.password?url.href:''; }
  catch { return ''; }
}
function renderPosts(posts) {
  document.getElementById('topPosts').innerHTML=posts.length?posts.map(post=>{
    const url=analyticsSafeUrl(post.url), image=analyticsSafeUrl(post.image_url), tag=url?'a':'article';
    return `<${tag} class="analytics-post" ${url?`href="${analyticsEsc(url)}" target="_blank" rel="noopener"`:''}>
    ${image?`<img src="${analyticsEsc(image)}" alt="">`:`<span class="analytics-post-art ${post.platform}">${analyticsIcon(post.platform)}</span>`}
    <div><span class="post-channel">${analyticsPlatform(post.platform)}</span><p>${analyticsEsc((post.text||'Media post').slice(0,170))}</p><dl>
    ${[['Likes','likes'],['Comments','comments'],['Shares','shares'],['Views','views']].map(([label,key])=>`<div><dt>${label}</dt><dd>${analyticsNumber(post[key])}</dd></div>`).join('')}
    </dl></div></${tag}>`;
  }).join(''):'<div class="analytics-empty">No dated posts are available for this period. Try 30 days or create your next post in Studio.</div>';
}

let analyticsRequest=0, analyticsAnswerRequest=0;
function showResultPanels(visible){document.querySelectorAll('.analytics-split,.content-panel,.analytics-ask').forEach(el=>el.hidden=!visible);}
async function loadAnalytics(){
  const request=++analyticsRequest;
  ++analyticsAnswerRequest;
  document.getElementById('analyticsAnswer').hidden=true;
  document.getElementById('analyticsRefresh').disabled=true;
  document.querySelector('#analyticsQuestion button').disabled=false;
  document.getElementById('analyticsNote').textContent='Checking your accounts…';
  document.getElementById('analyticsKpis').innerHTML='<p class="analytics-loading">Loading results…</p>';
  showResultPanels(false);
  try{
    const days=document.getElementById('analyticsWindow').value;
    const data=await analyticsApi('/api/analytics/dashboard?days='+encodeURIComponent(days));
    if(request!==analyticsRequest)return;
    const connected=Object.values(data.platforms||{}).some(p=>p.connected);
    if(!connected){
      document.getElementById('analyticsNote').textContent='';
      document.getElementById('analyticsKpis').innerHTML='<div class="analytics-empty"><h2>See what connects with your audience</h2><p>Connect an account to see available results and decide what to try next.</p><a class="button primary" href="/account#socials">Connect an account</a> <a href="/studio">Back to Studio</a></div>';
      return;
    }
    showResultPanels(true);
    const missing=(data.unavailable||[]).map(analyticsPlatform);
    document.getElementById('analyticsNote').textContent='Checked '+new Date(data.fetched_at).toLocaleString()+'. '+(missing.length?'Some results unavailable: '+missing.join(', ')+'.':'Platforms may update their counters later.');
    if(data.recommendation_history_saved===false)document.getElementById('analyticsNote').textContent+=' Next move could not save these results; refresh to try again.';
    renderKpis(data.summary||{});renderPlatforms(data.platforms||{});renderRecommendations(data.recommendations||[]);renderPosts(data.top_posts||[]);
  }catch(error){
    if(request!==analyticsRequest)return;
    document.getElementById('analyticsNote').textContent='Results could not be updated.';
    document.getElementById('analyticsKpis').innerHTML=`<div class="analytics-error">${analyticsEsc(error.message)} Use Refresh to try again.</div>`;
    showResultPanels(false);
  }finally{if(request===analyticsRequest)document.getElementById('analyticsRefresh').disabled=false;}
}
async function askAnalytics(question){
  const request=++analyticsAnswerRequest,windowRequest=analyticsRequest;
  const answer=document.getElementById('analyticsAnswer'),button=document.querySelector('#analyticsQuestion button');
  answer.hidden=false;answer.textContent='Reading the available results…';button.disabled=true;
  try{
    const result=await analyticsApi('/api/insights',{method:'POST',headers:{'Content-Type':'application/json','X-Zova-Request':'1'},body:JSON.stringify({question,days:Number(document.getElementById('analyticsWindow').value)})});
    if(request!==analyticsAnswerRequest||windowRequest!==analyticsRequest)return;
    answer.textContent=result.answer;
  }catch(error){if(request===analyticsAnswerRequest&&windowRequest===analyticsRequest)answer.textContent=error.message;}
  finally{if(request===analyticsAnswerRequest){button.disabled=false;if(document.activeElement===document.body)document.getElementById('analyticsQuestionText').focus?.();}}
}

document.getElementById("analyticsQuestion").addEventListener("submit",event=>{event.preventDefault();const field=document.getElementById("analyticsQuestionText"),question=field.value.trim();if(question)askAnalytics(question);});
document.querySelectorAll(".analytics-prompts button").forEach(button=>button.addEventListener("click",()=>{document.getElementById("analyticsQuestionText").value=button.textContent;askAnalytics(button.textContent);}));
document.getElementById("analyticsRefresh").addEventListener("click",loadAnalytics);
document.getElementById("analyticsWindow").addEventListener("change",loadAnalytics);
loadAnalytics();
