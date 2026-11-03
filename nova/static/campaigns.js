(() => {
  const element = id => document.getElementById(id);
  const form = element('campaign-form'), list = element('campaign-list');
  const status = element('campaign-status');
  const records = new Map(), uploaded = new Map();
  let current = null, busy = false;
  const selectedFiles = new Set();
  const picker = form.elements.files, drop = element('campaign-drop');
  function renderFiles() {
    const rows = element('campaign-files');
    rows.replaceChildren();
    for (const file of selectedFiles) {
      const row = document.createElement('li'), name = document.createElement('span'), remove = document.createElement('button');
      name.textContent = file.name;
      remove.type = 'button'; remove.textContent = 'Remove';
      remove.setAttribute('aria-label','Remove '+file.name);
      remove.onclick = () => { selectedFiles.delete(file); uploaded.delete(file); renderFiles(); status.textContent=''; picker.focus(); };
      row.append(name,remove); rows.append(row);
    }
    element('campaign-file-count').textContent = selectedFiles.size ? selectedFiles.size+' of 10 files selected' : 'Choose or drop up to 10 files';
  }
  function addFiles(files) {
    if (busy || !files.length) return;
    if (selectedFiles.size + files.length > 10) {
      status.textContent='Choose up to 10 files in total. Your previous selection is kept.';
      return;
    }
    for (const file of files) selectedFiles.add(file);
    renderFiles(); status.textContent='';
  }
  picker.onchange = () => { addFiles(Array.from(picker.files)); picker.value=''; };
  drop.ondragover = event => { event.preventDefault(); if (!busy) drop.classList.add('drag-over'); };
  drop.ondragleave = () => drop.classList.remove('drag-over');
  drop.ondrop = event => {
    event.preventDefault(); drop.classList.remove('drag-over'); addFiles(Array.from(event.dataTransfer.files));
  };
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
      const wrap=document.createElement('label'); control.setAttribute('aria-label',label); wrap.append(label,control); panel.append(wrap); return control;
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
    })), 'Post updated.');
    const markEditing=()=>{
      for(const item of document.querySelectorAll('#campaign-review button,#campaign-review summary,#campaign-list')) {
        if(item===save || panel.contains(item)) continue;
        if(item.tagName==='SUMMARY') item.closest('details').inert=true;
        else item.disabled=true;
      }
      panel.dataset.dirty='true';
    };
    panel.addEventListener('input',markEditing);
    const cancel=document.createElement('button');cancel.textContent='Cancel';
    cancel.onclick=()=>{list.disabled=false;show(row);element('campaign-revise').disabled=false;element('campaign-accept').disabled=false;};
    panel.append(cancel);
    summary.onclick=event=>{if(panel.dataset.dirty==='true')event.preventDefault();};
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
    element('campaign-media').hidden = !row.assets.length;
    element('campaign-media').textContent = row.assets.map(a => a.name).join(' · ');
    const cards = element('campaign-posts');
    cards.replaceChildren();
    row.posts.forEach((post,i) => {
      const card = document.createElement('article'), title = document.createElement('strong'), text = document.createElement('p');
      title.textContent = ({x:'X',facebook:'Facebook',instagram:'Instagram',tiktok:'TikTok'}[post.platform] || post.platform) + ' · ' + new Date(row.dates[i].utc).toLocaleString(undefined,{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit',timeZone:row.brief.timezone,timeZoneName:'short'});
      text.textContent = post.caption;
      card.append(title,text);
      const asset = row.assets.find(a => a.id === post.asset_id);
      if (asset) card.append(document.createTextNode(asset.name + ' '));
      if (!row.draft_ids.length || post.editable) editCard(card,row,i);
      if (post.status) {const state=document.createElement('small');state.className='campaign-post-state';state.textContent=post.status.replaceAll('_',' ');title.append(state);}
      if(post.schedule){
        const panel=document.createElement('details'),open=document.createElement('summary');
        open.textContent='Change time';panel.append(open);
        const time=document.createElement('input');time.type='datetime-local';time.value=row.dates[i].local.slice(0,16);
        time.setAttribute('aria-label','New time · '+row.brief.timezone);panel.append(time);
        const save=document.createElement('button');save.textContent='Reschedule';panel.append(save);
        save.onclick=()=>run(async()=>{
          await request('/api/schedules/'+post.schedule.id+'/reschedule',{scheduled_local:time.value,timezone:row.brief.timezone,expected_updated_at:post.schedule.updated_at});
          show(await request('/api/campaigns/'+row.id));
        });card.append(panel);
      }
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
        link.textContent = 'Open in Studio'; card.append(link);
      }
      cards.append(card);
    });
    element('campaign-feedback').value = row.feedback || '';
    element('campaign-actions').hidden = !!row.draft_ids.length;
    element('campaign-accept').hidden = !row.posts.length;
    element('campaign-revise').textContent = row.posts.length ? 'Update plan' : 'Generate plan';
  }
  async function run(action, successMessage='') {
    if (busy) return;
    busy = true;
    const controls = document.querySelectorAll('main input,main select,main button,main textarea');
    controls.forEach(control => control.disabled = true);
    status.textContent = 'Working…';
    try { await action(); status.textContent = successMessage; }
    catch (error) { status.textContent = error.message; }
    finally {
      controls.forEach(control => control.disabled = false); busy = false;
      document.querySelector('#campaign-review details[data-dirty="true"] textarea')?.dispatchEvent(new Event('input',{bubbles:true}));
    }
  }
  window.addEventListener('beforeunload',event=>{
    if(document.querySelector('#campaign-review details[data-dirty="true"]')){event.preventDefault();event.returnValue='';}
  });
  const generate = async feedback => show(await request('/api/ai/campaigns/'+current.id+'/plan',{revision:current.revision,feedback}));
  list.onchange = () => run(async () => show(list.value ? await request('/api/campaigns/'+Number(list.value)) : null));
  form.onsubmit = event => {
    event.preventDefault();
    const data = new FormData(form), files = Array.from(selectedFiles), platforms = data.getAll('platform');
    run(async () => {
      if (!platforms.length || Number(data.get('count')) < platforms.length) throw new Error('Choose at least one post per selected platform.');
      if (files.length > 10) throw new Error('Choose up to ten files.');
      const media = [];
      for (const [index,file] of files.entries()) {
        if (!uploaded.has(file)) {
          status.textContent='Uploading '+(index+1)+' of '+files.length+' · '+file.name;
          const upload = new FormData(); upload.append('files',file);
          try { uploaded.set(file,(await request('/api/media',upload)).assets[0].id); }
          catch (error) { throw new Error(file.name+' — '+error.message); }
        }
        media.push(uploaded.get(file));
      }
      show(await request('/api/campaigns',{idea:data.get('idea'),platforms,media,start:data.get('start'),
        timezone:Intl.DateTimeFormat().resolvedOptions().timeZone,count:Number(data.get('count')),frequency:data.get('frequency')}));
      form.reset(); uploaded.clear(); selectedFiles.clear(); renderFiles();
      await generate('');
    });
  };
  element('campaign-revise').onclick = () => run(() => generate(element('campaign-feedback').value));
  element('campaign-accept').onclick = () => run(async () => {await request('/api/campaigns/'+current.id+'/accept',{revision:current.revision});show(await request('/api/campaigns/'+current.id));}, 'Drafts added to Schedule.');
  run(async () => {
    (await request('/api/campaigns')).forEach(remember);
    const id=Number(new URL(location.href).searchParams.get('campaign'));
    if(records.has(id)) show(await request('/api/campaigns/'+id));
  });
})();
