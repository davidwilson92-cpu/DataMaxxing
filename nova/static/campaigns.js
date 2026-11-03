(() => {
  const element = id => document.getElementById(id);
  const form = element('campaign-form'), list = element('campaign-list');
  const status = element('campaign-status');
  const records = new Map(), uploaded = new Map();
  let current = null, busy = false;
  async function request(path, body) {
    const options = body instanceof FormData ? {method:'POST',body}
      : body ? {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)} : {};
    const response = await fetch(path,options);
    const result = await response.json();
    if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'Check your campaign details and try again.');
    return result;
  }
  function remember(row) {
    if (!records.has(row.id)) list.add(new Option(row.brief.idea.slice(0,70),row.id));
    records.set(row.id,row);
  }
  function editCard(card,row,index) {
    const post=row.posts[index], panel=document.createElement('details'), summary=document.createElement('summary');
    summary.textContent='Edit post'; panel.append(summary);
    function field(label,control) {
      const wrap=document.createElement('label'); wrap.append(label,control); panel.append(wrap); return control;
    }
    const caption=field('Caption',document.createElement('textarea')); caption.value=post.caption;
    const platform=field('Platform',document.createElement('select'));
    for (const [value,name] of Object.entries({instagram:'Instagram',facebook:'Facebook',x:'X',tiktok:'TikTok'})) platform.add(new Option(name,value));
    platform.value=post.platform;
    const media=field('Media',document.createElement('select')); media.add(new Option('No attachment',''));
    for (const a of row.assets) media.add(new Option(a.name,String(a.id)));
    if (post.asset_id && !row.assets.some(a=>a.id===post.asset_id)) media.add(new Option('Current attachment',String(post.asset_id)));
    media.value=post.asset_id || '';
    const time=field('Planned time · '+row.brief.timezone,document.createElement('input'));
    time.type='datetime-local'; time.value=row.dates[index].local.slice(0,16);
    const save=document.createElement('button'); save.textContent='Save changes'; panel.append(save);
    save.onclick=()=>run(async()=>show(await request('/api/campaigns/'+row.id+'/posts/'+index,{
      revision:row.revision, draft_revision:post.draft_revision,series_revision:post.series_revision,
      caption:caption.value,platform:platform.value,asset_id:Number(media.value)||null,local_time:time.value
    })));
    panel.ontoggle=()=>{
      if(panel.open && card.isConnected) for (const other of card.parentElement.querySelectorAll('details[open]')) if(other!==panel) other.open=false;
    };
    card.append(panel);
  }
  function show(row) {
    current = row;
    form.hidden = !!row;
    element('campaign-review').hidden = !row;
    if (!row) return;
    remember(row);
    list.value = String(row.id);
    element('campaign-title').textContent = row.brief.idea;
    element('campaign-media').textContent = row.assets.map(a => a.name).join(' · ');
    const cards = element('campaign-posts');
    cards.replaceChildren();
    row.posts.forEach((post,i) => {
      const card = document.createElement('article'), title = document.createElement('strong'), text = document.createElement('p');
      title.textContent = post.platform + ' · ' + new Date(row.dates[i].utc).toLocaleString(undefined,{timeZone:row.brief.timezone,timeZoneName:'short'});
      text.textContent = post.caption;
      card.append(title,text);
      const asset = row.assets.find(a => a.id === post.asset_id);
      if (asset) card.append(document.createTextNode(asset.name + ' '));
      if (!row.draft_ids.length || post.editable) editCard(card,row,i);
      if (post.status) {const state=document.createElement('small');state.textContent=post.status.replaceAll('_',' ');card.append(state);}
      if (post.status==='scheduled') {
        const edit=document.createElement('button'); edit.textContent='Unschedule to edit';
        edit.onclick=()=>run(async()=>{
          await request('/api/schedules/drafts/'+row.draft_ids[i]+'/edit',{revision:post.draft_revision});
          show(await request('/api/campaigns/'+row.id));
        }); card.append(edit);
      }
      if (row.draft_ids[i] && post.status!=='removed') {
        const link = document.createElement('a');
        link.href = '/studio?draft='+row.draft_ids[i]+'&workspace='+document.querySelector('meta[name=zova-workspace]').content;
        link.textContent = 'Open draft'; card.append(link);
      }
      cards.append(card);
    });
    element('campaign-feedback').value = row.feedback || '';
    element('campaign-actions').hidden = !!row.draft_ids.length;
    element('campaign-accept').hidden = !row.posts.length;
    element('campaign-revise').textContent = row.posts.length ? 'Update plan' : 'Generate plan';
  }
  async function run(action) {
    if (busy) return;
    busy = true;
    const controls = document.querySelectorAll('main input,main select,main button,main textarea');
    controls.forEach(control => control.disabled = true);
    status.textContent = 'Working…';
    try { await action(); status.textContent = current?.draft_ids.length ? 'Drafts saved. Review each post before publishing.' : ''; }
    catch (error) { status.textContent = error.message; }
    finally { controls.forEach(control => control.disabled = false); busy = false; }
  }
  const generate = async feedback => show(await request('/api/ai/campaigns/'+current.id+'/plan',{revision:current.revision,feedback}));
  list.onchange = () => run(async () => show(list.value ? await request('/api/campaigns/'+Number(list.value)) : null));
  form.onsubmit = event => {
    event.preventDefault();
    const data = new FormData(form), files = Array.from(form.elements.files.files), platforms = data.getAll('platform');
    run(async () => {
      if (!platforms.length || Number(data.get('count')) < platforms.length) throw new Error('Choose at least one post per selected platform.');
      if (files.length > 10) throw new Error('Choose up to ten files.');
      const media = [];
      for (const file of files) {
        if (!uploaded.has(file)) {
          const upload = new FormData(); upload.append('files',file);
          uploaded.set(file,(await request('/api/media',upload)).assets[0].id);
        }
        media.push(uploaded.get(file));
      }
      show(await request('/api/campaigns',{idea:data.get('idea'),platforms,media,start:data.get('start'),
        timezone:Intl.DateTimeFormat().resolvedOptions().timeZone,count:Number(data.get('count')),frequency:data.get('frequency')}));
      form.reset(); uploaded.clear();
      await generate('');
    });
  };
  element('campaign-revise').onclick = () => run(() => generate(element('campaign-feedback').value));
  element('campaign-accept').onclick = () => run(async () => {await request('/api/campaigns/'+current.id+'/accept',{revision:current.revision});show(await request('/api/campaigns/'+current.id));});
  run(async () => (await request('/api/campaigns')).forEach(remember));
})();
