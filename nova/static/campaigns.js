(() => {
  const element = id => document.getElementById(id);
  const form = element('campaign-form'), list = element('campaign-list');
  const status = element('campaign-status');
  const records = new Map(), uploaded = new Map();
  let current = null, busy = false, briefReady = false, revision = 0, saved = '', writing = null;
  let zone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  const saveNote = element('brief-save');
  function nameOf(row){return row.name || 'Campaign '+row.id;}
  const timingField=form.elements.timing,startField=form.elements.start;
  function startValue(){return startField.type==='date' && startField.value ? startField.value+'T23:00' : startField.value;}
  function setTimeMode(value){
    const prior=startField.value;
    timingField.value=value;
    startField.type=value==='suggest'?'date':'datetime-local';
    startField.value=prior ? (value==='suggest'?prior.slice(0,10):prior.length===10?prior+'T12:00':prior) : '';
  }
  timingField.onchange=()=>{setTimeMode(timingField.value);changed();};
  setTimeMode('suggest');
  function snapshot() {
    return JSON.stringify({name:form.elements.namedItem("name").value,recommend_times:form.elements.timing.value==="suggest",idea:form.elements.idea.value,platforms:[...form.querySelectorAll('[name=platform]:checked')].map(el=>el.value),
      start:startValue(), timezone:zone, frequency:form.elements.frequency.value,
      count:form.elements.count.valueAsNumber || null, media:[...selectedFiles].map(file=>uploaded.get(file)).filter(Boolean)});
  }
  async function flush() {
    clearTimeout(timer);
    if (!briefReady) throw new Error('Reopen Campaign to load your saved brief.');
    if (!writing && saved!==snapshot()) {
      writing=(async()=>{
        while(saved!==snapshot()) {
          const next=snapshot(); saveNote.textContent='Saving brief…';
          const result=await request('/api/campaign-brief',{...JSON.parse(next),revision});
          revision=result.revision; saved=next;
        }
        saveNote.textContent='Brief saved';
      })().catch(error=>{saveNote.textContent='Brief not saved. '+error.message;throw error;}).finally(()=>{writing=null;});
    }
    if(writing) await writing;
  }
  let timer;
  const changed=()=>{clearTimeout(timer);if(briefReady) timer=setTimeout(()=>flush().catch(()=>{}),250);};
  async function restore() {
    const result=await request('/api/campaign-brief');
    revision=result.revision;const draft=result.brief;
    if(draft){
      setTimeMode(draft.recommend_times?'suggest':'manual');
      startField.value=draft.recommend_times?draft.start.slice(0,10):draft.start;
      for(const key of ['name','idea','frequency','count']) form.elements[key].value=draft[key]??'';
      form.querySelectorAll('[name=platform]').forEach(el=>el.checked=draft.platforms.includes(el.value));
      zone=draft.timezone;
      for(const a of draft.assets){const file={name:a.filename};selectedFiles.add(file);uploaded.set(file,a.id);}
      renderFiles();saveNote.textContent='Brief restored';
    }
    saved=snapshot();briefReady=true;
  }
  form.addEventListener('input',event=>{if(event.target.type!=='file') changed();});
  document.addEventListener('click',event=>{
    const link=event.target.closest('a[href]');
    if(!link || current || !briefReady || (saved===snapshot()&&!writing) || event.ctrlKey || event.metaKey) return;
    event.preventDefault();flush().then(()=>location.assign(link.href)).catch(()=>{});
  });
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
      remove.onclick = () => { selectedFiles.delete(file); uploaded.delete(file); renderFiles(); changed(); status.textContent=''; picker.focus(); };
      const id=uploaded.get(file);
      if(id){const preview=document.createElement('img');preview.loading='lazy';preview.alt='';preview.src=window.zovaWorkspaceUrl('/media/thumbnail/'+id);row.append(preview);}
      row.append(name,remove); rows.append(row);
    }
    element('retry-campaign-uploads').hidden=![...selectedFiles].some(file=>!uploaded.has(file));
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
    run(async()=>{await uploadPending();await flush();});
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
    if (!records.has(row.id)) list.add(new Option(nameOf(row),row.id));
    else Array.from(list.options).find(option=>Number(option.value)===row.id).text=nameOf(row);
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
    const suggest=document.createElement('button');suggest.textContent='Suggest time';panel.append(suggest);
    const reason=document.createElement('small');panel.append(reason);
    suggest.onclick=()=>run(async()=>{const suggestions=await request('/api/campaigns/'+row.id+'/timing');time.value=suggestions[index].local.slice(0,16);reason.textContent=suggestions[index].reason;time.dispatchEvent(new Event('input',{bubbles:true}));});
    const save=document.createElement('button'); save.textContent='Save changes'; panel.append(save);
    save.onclick=()=>run(async()=>show(await request('/api/campaigns/'+row.id+'/posts/'+index,{
      revision:row.revision, draft_revision:post.draft_revision,series_revision:post.series_revision,
      caption:caption.value,platform:platform.value,asset_id:Number(media.value)||null,local_time:time.value
    })), 'Post updated.');
    const markEditing=()=>{
      for(const item of document.querySelectorAll('#campaign-review button,#campaign-review summary,#campaign-view,#campaign-sort,#campaign-list')) {
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
      if(panel.open && card.isConnected) for (const other of element('campaign-posts').querySelectorAll('details[open]')) if(other!==panel) other.open=false;
    };
    card.append(panel);
  }
  let selectedDay='', activeMonth='', calendarID=0;
  function drawCalendar(slots){
    const host=element('campaign-calendar');host.replaceChildren();
    if(calendarID!==current.id||!selectedDay){selectedDay=slots.map(s=>s.day).sort()[0]||current.brief.start.slice(0,10);activeMonth=selectedDay.slice(0,7);calendarID=current.id;}
    const [y,m]=activeMonth.split('-').map(Number), first=new Date(Date.UTC(y,m-1,1));
    const nav=document.createElement('div');nav.className='campaign-calendar-nav';
    const monthName=first.toLocaleString(undefined,{month:'long',year:'numeric',timeZone:'UTC'});
    for(const [label,delta] of [['Previous month',-1],[monthName,0],['Next month',1]]){
      const el=document.createElement(delta?'button':'strong');el.textContent=delta<0?'‹':delta>0?'›':label;
      if(delta){el.setAttribute('aria-label',label);el.onclick=()=>{activeMonth=new Date(Date.UTC(y,m-1+delta,1)).toISOString().slice(0,7);selectedDay=slots.map(s=>s.day).sort().find(d=>d.startsWith(activeMonth))||activeMonth+'-01';show(current);};}
      nav.append(el);
    }
    const grid=document.createElement('div');grid.className='campaign-calendar-grid';
    for(const day of ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']){const cell=document.createElement('b');cell.textContent=day;grid.append(cell);}
    for(let i=0;i<(first.getUTCDay()+6)%7;i++)grid.append(document.createElement('span'));
    for(let d=1;d<=new Date(Date.UTC(y,m,0)).getUTCDate();d++){
      const day=activeMonth+'-'+String(d).padStart(2,'0'),daySlots=slots.filter(s=>s.day===day),n=daySlots.length;
      const cell=document.createElement(n?'button':'span');cell.textContent=d;
      if(n){const label=n===1?'1 post':n+' posts';const badge=document.createElement('small');const platforms=[...new Set(daySlots.map(s=>s.post.platform))].sort();badge.className='calendar-marks';badge.innerHTML=platforms.map(platform=>window.zovaPlatformLabel(platform)).join('');cell.append(badge);
        cell.setAttribute('aria-label',day+', '+label+', '+platforms.join(', '));cell.setAttribute('aria-pressed',String(selectedDay===day));cell.onclick=()=>{selectedDay=day;show(current);};}
      grid.append(cell);
    }
    host.append(nav,grid);if(!slots.some(s=>s.day.startsWith(activeMonth))) host.append('No posts this month.');
  }
  element('campaign-view').onchange=element('campaign-sort').onchange=()=>show(current);
  const nameForm=element('campaign-name-form');
  element('rename-campaign').onclick=()=>{element('campaign-tools').open=false;nameForm.hidden=false;nameForm.elements.name.value=nameOf(current);nameForm.elements.name.focus();};
  nameForm.onsubmit=event=>{event.preventDefault();run(async()=>show(await request('/api/campaigns/'+current.id+'/name',{revision:current.revision,name:nameForm.elements.name.value})));};
  function show(row) {
    current = row;
    form.hidden = !!row;
    element('campaign-review').hidden = !row;
    element('campaign-heading').textContent=row?nameOf(row):'Campaigns';
    element('campaign-name-form').hidden=true;
    if (!row) return;
    document.querySelectorAll('#campaign-review button,#campaign-view,#campaign-sort,#campaign-list').forEach(control=>control.disabled=false);
    remember(row);
    list.value = String(row.id);
    element('campaign-media').hidden = true;
    element('campaign-media').textContent = row.assets.map(a => a.name).join(' · ');
    const cards = element('campaign-posts');
    cards.replaceChildren();
    const slots = row.posts.map((post,i)=>{
      const asset=row.assets.find(a=>a.id===post.asset_id);
      const kind=post.media_kind || asset?.kind || (!post.asset_id?'text':/\.(mov|mp4|webm)$/i.test(asset?.name||'')?'video':'image');
      return {post,i,kind,day:row.dates[i].local.slice(0,10)};
    });
    const group=element('campaign-sort').value;
    slots.sort((a,b)=>(group==='platform'?a.post.platform.localeCompare(b.post.platform):group==='media'?a.kind.localeCompare(b.kind):0) ||
      Date.parse(row.dates[a.i].utc)-Date.parse(row.dates[b.i].utc) || a.i-b.i);
    const calendar=element('campaign-view').value==='calendar';element('campaign-calendar').hidden=!calendar;
    if(calendar) drawCalendar(slots);
    slots.filter(s=>!calendar || s.day===selectedDay).forEach(({post,i,kind}) => {
      const card = document.createElement('article'), title = document.createElement('strong'), text = document.createElement('p');
      title.className='platform-strip';title.dataset.platform=post.platform;
      const mark=document.createElement('span');mark.className='platform-mark';mark.setAttribute('aria-hidden','true');
      mark.innerHTML=window.zovaPlatformLabel(post.platform);
      const word=document.createElement('b');word.textContent=({x:'X',facebook:'Facebook',instagram:'Instagram',tiktok:'TikTok'})[post.platform];
      const date=document.createElement('time');date.dateTime=row.dates[i].utc;
      date.textContent=new Date(date.dateTime).toLocaleString(undefined,{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit',timeZone:row.brief.timezone,timeZoneName:'short'});
      title.append(mark,word,date);card.append(title);
      for(const id of post.media_ids || (post.asset_id?[post.asset_id]:[])){
        const asset=row.assets.find(a=>a.id===id);
        const video=(asset?.kind || kind)==='video';
        const preview=document.createElement(video?'video':'img');preview.className='post-media';
        if(video){preview.controls=true;preview.playsInline=true;preview.preload='none';preview.poster=window.zovaWorkspaceUrl('/media/thumbnail/'+id);}
        else {preview.loading='lazy';preview.alt=asset?.name||'Post image';}
        preview.src=window.zovaWorkspaceUrl((video?'/media/preview/':'/media/thumbnail/')+id);card.append(preview);
      }
      text.textContent=post.caption;card.append(text);
      if(row.dates[i].reason){const why=document.createElement('small');why.className='timing-reason';why.textContent=row.dates[i].reason;card.append(why);}
      if(post.timing_warning){const note=document.createElement('p');note.setAttribute('role','status');note.textContent=post.timing_warning;card.append(note);}
      const footer=document.createElement('div');footer.className='post-actions';card.append(footer);
      if (!row.draft_ids.length || post.editable) editCard(footer,row,i);
      if (post.status) {const state=document.createElement('small');state.className='campaign-post-state';state.textContent=post.status.replaceAll('_',' ');footer.append(state);}
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
        link.textContent = 'Open in Studio'; footer.append(link);
      }
      cards.append(card);
    });
    element('campaign-feedback').value = row.feedback || '';
    element('campaign-actions').hidden = !!row.draft_ids.length;
    element('campaign-feedback').closest('label').hidden=!!row.posts.length;
    element('campaign-revise').hidden=!!row.posts.length;
    element('campaign-accept').hidden = !row.posts.length;
    element('campaign-revise').textContent = row.posts.length ? 'Update plan' : 'Generate plan';
    showControls(row);
  }
  let controlAction='', reuseKey='';
  const controlForm=element('campaign-control-form');
  const toolsMenu=element('campaign-tools');
  document.addEventListener('click',event=>{if(toolsMenu.open&&!toolsMenu.contains(event.target))toolsMenu.open=false;});
  toolsMenu.addEventListener('keydown',event=>{
    if(event.key==='Escape'&&toolsMenu.open){toolsMenu.open=false;toolsMenu.querySelector('summary').focus();event.preventDefault();}
  });
  const actionNames={pause:'Pause campaign',resume:'Resume campaign',move:'Move remaining dates',reuse:'Reuse campaign',extend:'Add posts',improve:'Improve remaining posts'};
  async function openControl(action) {
    show(await request('/api/campaigns/'+current.id));
    controlAction=action;reuseKey=crypto.randomUUID();
    controlForm.dataset.campaign=String(current.id);
    element('campaign-tools').open=false;controlForm.hidden=false;
    element('campaign-control-title').textContent=actionNames[action];
    element('campaign-control-submit').textContent=['improve','extend'].includes(action)?'Preview changes':action==='reuse'?'Create copy':actionNames[action];
    element('campaign-control-note').textContent=({pause:'Stops remaining scheduled posts. Resume will keep them as drafts for final review.',resume:'Posts remain drafts until you review and schedule them.',move:'Moves remaining posts together. Scheduled posts return to drafts for final review.',reuse:'Copies captions and media into a new plan. Review date-sensitive wording before scheduling.',improve:'Preview caption changes. Applying them returns scheduled posts to drafts for final approval.',extend:'Preview new follow-ups using your campaign, strategy, voice and available results.'})[action];
    for(const [key,visible] of Object.entries({name:action==='reuse',start:['reuse','move','extend'].includes(action),count:action==='extend',feedback:['improve','extend'].includes(action)})) {
      element('control-'+key+'-label').hidden=!visible;
    }
    controlForm.elements.copy_name.required=action==='reuse';controlForm.elements.new_start.required=['reuse','move','extend'].includes(action);
    controlForm.elements.copy_name.value=(nameOf(current)+' copy').slice(0,80);
    controlForm.elements.new_start.value='';controlForm.elements.feedback.value='';controlForm.elements.extra_count.value='2';
    element('control-start-label').firstChild.textContent='First post · '+current.brief.timezone;
    controlForm.scrollIntoView({block:'nearest'});
    setTimeout(()=>controlForm.querySelector('label:not([hidden]) input,label:not([hidden]) textarea,button').focus(),0);
  }
  element('improve-remaining').onclick=()=>run(()=>openControl('improve'));
  for(const button of document.querySelectorAll('[data-campaign-action]')) button.onclick=()=>run(()=>openControl(button.dataset.campaignAction==='pause'&&current.state==='paused'?'resume':button.dataset.campaignAction));
  element('campaign-control-cancel').onclick=()=>{
    controlForm.hidden=true;
    const improve=element('improve-remaining');
    (controlAction==='improve'&&!improve.hidden?improve:element('campaign-tools').querySelector('summary')).focus();
  };
  controlForm.onsubmit=event=>{event.preventDefault();run(async()=>{
    const revision=current.revision,base='/api/campaigns/'+current.id;
    let path=base+'/control',body={revision,action:controlAction,snapshot:current.control_snapshot,start:controlForm.elements.new_start.value};
    if(controlAction==='reuse'){path=base+'/reuse';body={revision,name:controlForm.elements.copy_name.value,start:controlForm.elements.new_start.value,request_key:reuseKey};}
    if(['improve','extend'].includes(controlAction)){path='/api/ai/campaigns/'+current.id+'/improve';body={revision,mode:controlAction,feedback:controlForm.elements.feedback.value,count:Number(controlForm.elements.extra_count.value),start:controlForm.elements.new_start.value};}
    const updated=await request(path,body);controlForm.hidden=true;show(updated);
  },['pause','resume','move'].includes(controlAction)?'Saved. Review drafts before scheduling.':controlAction==='reuse'?'Copy saved. Review its dates and captions.':'Changes ready to review.');};
  function showControls(row){
    if(controlForm.dataset.campaign!==String(row.id))controlForm.hidden=true;
    element('campaign-tools').inert=false;
    element('campaign-state').textContent=row.state==='paused'?'Paused · drafts kept':'';
    document.querySelector('[data-campaign-action="pause"]').textContent=row.state==='paused'?'Resume campaign':'Pause campaign';
    element('improve-remaining').hidden=!row.posts.some(post=>['draft','scheduled'].includes(post.status||'draft') && (!row.draft_ids.length||post.simple));
    const panel=element('campaign-suggestion');panel.replaceChildren();panel.hidden=!row.suggestion;
    if(!row.suggestion)return;
    const proposal=row.suggestion,title=document.createElement('h2'),basis=document.createElement('p');
    title.textContent=proposal.mode==='extend'?'New follow-ups':'Proposed improvements';basis.textContent=proposal.posts.length+(proposal.posts.length===1?' post · ':' posts · ')+proposal.basis;panel.append(title,basis);
    if(proposal.positions.some(i=>row.posts[i]?.status==='scheduled')){const notice=document.createElement('p');notice.textContent='Applying changes unschedules these posts. Review them again before publishing.';panel.append(notice);}
    proposal.posts.forEach((post,n)=>{
      const card=document.createElement('article'),label=document.createElement('strong'),text=document.createElement('p');
      label.textContent=({instagram:'Instagram',facebook:'Facebook',x:'X',tiktok:'TikTok'})[post.platform]+' · '+new Date(proposal.dates[n].utc).toLocaleString(undefined,{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit',timeZone:row.brief.timezone,timeZoneName:'short'});text.textContent=post.caption;card.append(label,text);
      if(post.asset_id){const media=document.createElement('img');media.src=window.zovaWorkspaceUrl('/media/thumbnail/'+post.asset_id);media.alt=row.assets.find(a=>a.id===post.asset_id)?.name||'Post attachment';media.loading='lazy';media.className='proposal-media';card.append(media);}
      const previous=row.posts[proposal.positions[n]];
      if(previous){const old=document.createElement('details'),summary=document.createElement('summary'),caption=document.createElement('p');summary.textContent='Original caption';caption.textContent=previous.caption;old.append(summary,caption);card.append(old);}
      panel.append(card);
    });
    const actions=document.createElement('div');actions.className='campaign-inline-actions';
    for(const [action,label] of [['apply','Apply changes'],['discard','Keep originals']]){
      const button=document.createElement('button');button.type='button';button.textContent=label;if(action==='apply')button.className='button';
      button.onclick=()=>run(async()=>show(await request('/api/campaigns/'+row.id+'/suggestion',{revision:row.revision,action})),action==='apply'?'Drafts updated. Nothing has been published.':'Originals kept.');actions.append(button);
    }
    panel.append(actions);
  }
  function report(message, failed=false) {
    const proposal=element('campaign-suggestion');
    const target=!controlForm.hidden ? controlForm : !proposal.hidden ? proposal : current ? element('campaign-review').querySelector('.campaign-control-bar') : form;
    target.append(status);status.textContent=message;
    if(failed)status.scrollIntoView({block:'nearest'});
  }
  async function run(action, successMessage='') {
    if (busy) return;
    busy = true;
    const controls = document.querySelectorAll('main input,main select,main button,main textarea');
    controls.forEach(control => control.disabled = true);
    report('Working…');
    try { await action(); report(successMessage); }
    catch (error) { report(error.message,true); }
    finally {
      controls.forEach(control => control.disabled = false); busy = false;
      document.querySelector('#campaign-review details[data-dirty="true"] textarea')?.dispatchEvent(new Event('input',{bubbles:true}));
    }
  }
  window.addEventListener('beforeunload',event=>{
    if((briefReady && !current && (writing || saved!==snapshot() || [...selectedFiles].some(f=>!uploaded.has(f)))) || document.querySelector('#campaign-review details[data-dirty="true"]')){event.preventDefault();event.returnValue='';}
  });
  const generate = async feedback => show(await request('/api/ai/campaigns/'+current.id+'/plan',{revision:current.revision,feedback}));
  list.onchange = () => run(async () => show(list.value ? await request('/api/campaigns/'+Number(list.value)) : null));
  async function uploadPending() {
    const files=Array.from(selectedFiles), failures=[];
    for(const [index,file] of files.entries()) {
      if(uploaded.has(file)) continue;
      status.textContent='Uploading '+(index+1)+' of '+files.length+' · '+file.name;
      const upload=new FormData();upload.append('files',file);
      try {uploaded.set(file,(await request('/api/media',upload)).assets[0].id);}
      catch(error){failures.push(file.name+' — '+error.message);continue;}
      await flush();
      renderFiles();
    }
    if(failures.length) throw new Error(failures.join(' · ')+' — Retry uploads.');
  }
  element('retry-campaign-uploads').onclick=()=>run(uploadPending);
  form.onsubmit = event => {
    event.preventDefault();
    const data = new FormData(form), files = Array.from(selectedFiles), platforms = data.getAll('platform');
    run(async () => {
      if (!platforms.length || Number(data.get('count')) < platforms.length) throw new Error('Choose at least one post per selected platform.');
      if (files.length > 10) throw new Error('Choose up to ten files.');
      const media = [];
      await uploadPending();
      await flush();
      for(const file of files) media.push(uploaded.get(file));
      show(await request('/api/campaigns',{name:data.get('name'),idea:data.get('idea'),platforms,media,start:startValue(),recommend_times:timingField.value==='suggest',
        timezone:zone,brief_revision:revision,count:Number(data.get('count')),frequency:data.get('frequency')}));
      form.reset();setTimeMode('suggest'); uploaded.clear(); selectedFiles.clear(); renderFiles();revision++;zone=Intl.DateTimeFormat().resolvedOptions().timeZone;saved=snapshot();saveNote.textContent='';
      await generate('');
    });
  };
  element('campaign-revise').onclick = () => run(() => generate(element('campaign-feedback').value));
  element('campaign-accept').onclick = () => run(async () => {await request('/api/campaigns/'+current.id+'/accept',{revision:current.revision});show(await request('/api/campaigns/'+current.id));}, 'Drafts added to Schedule.');
  run(async () => {
    (await request('/api/campaigns')).forEach(remember);await restore();
    const id=Number(new URL(location.href).searchParams.get('campaign'));
    if(records.has(id)) show(await request('/api/campaigns/'+id));
  });
})();
