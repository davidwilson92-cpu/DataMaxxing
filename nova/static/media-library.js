/* Private media stays in its existing workspace. No publication or deletion here. */
(() => {
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  window.zovaLearningMarkup = value => {
    if (!value) return '';
    const stale=value.checked_at && Date.now()-new Date(value.checked_at).getTime()>86400000;
    return `<details class="learning-evidence"><summary>${escape(stale?'Evidence needs refresh':value.sample_size?'Evidence · '+value.sample_size+' posts':'An idea to test')}</summary><p>${escape(value.summary)} ${escape(value.note)}</p>${value.checked_at?`<small>Checked ${escape(new Date(value.checked_at).toLocaleString())}</small>`:''}${(value.examples||[]).map(p=>`<blockquote><p>${escape(p.text||'Post without a caption')}</p><small>${escape(p.platform)} · ${escape(p.created_at||'Date unavailable')} · ${escape(p.format||'Format unavailable')}</small><p>${Object.entries(p.metrics).map(([k,v])=>escape(k)+': '+(v===null?'Unavailable':escape(v))).join(' · ')}</p></blockquote>`).join('')}</details>`;
  };
  window.zovaMediaLibrary = ({existing=[],limit=10,onSelect}) => {
    const previous=document.activeElement, workspace=document.querySelector('meta[name=zova-workspace]')?.content;
    const dialog=document.createElement('dialog');dialog.className='media-library';dialog.setAttribute('aria-label','Saved media');
    dialog.innerHTML='<header><h2>Saved media</h2><button type="button" aria-label="Close saved media">×</button></header><form class="library-search"><label>Search files<input name="q" type="search" maxlength="100"></label><label>Type<select name="kind"><option value="all">All media</option><option value="image">Photos</option><option value="video">Videos</option></select></label><button>Search</button></form><p role="status"></p><div class="library-assets"></div><button type="button" class="library-more" hidden>Load more</button><footer><span aria-live="polite">0 selected</span><button type="button" class="library-use" disabled>Use selected</button></footer>';
    document.body.append(dialog);
    const rows=dialog.querySelector('.library-assets'), status=dialog.querySelector('[role=status]'), form=dialog.querySelector('form'), use=dialog.querySelector('.library-use'), more=dialog.querySelector('.library-more'), selection=new Map();
    let cursor=null,busy=false,loading=false,controller=null,serial=0;
    const close=()=>{if(busy)return;dialog.close();};
    dialog.querySelector('header button').onclick=close;
    dialog.addEventListener('cancel',event=>{if(busy)event.preventDefault();});
    dialog.addEventListener('close',()=>{controller?.abort();dialog.remove();previous?.focus();});
    function render(asset){
      const article=document.createElement('article'), label=document.createElement('label'), check=document.createElement('input');
      check.type='checkbox';check.disabled=busy||existing.includes(asset.id);check.dataset.existing=String(existing.includes(asset.id));check.checked=existing.includes(asset.id)||selection.has(asset.id);
      const image=document.createElement('img');image.alt='';image.loading='lazy';image.src=window.zovaWorkspaceUrl(asset.thumbnail);image.onerror=()=>{image.hidden=true;};
      const title=document.createElement('span');title.textContent=asset.filename;
      label.append(check,image,title);article.append(label);
      const state=document.createElement('small');state.textContent=asset.states.map(s=>s.replaceAll('_',' ')).join(' · ');article.append(state);
      if(asset.uses.length){const details=document.createElement('details'),summary=document.createElement('summary');summary.textContent='Used in '+asset.uses.length+' places';details.append(summary);for(const used of asset.uses){const p=document.createElement('p');p.textContent=used.title+' · '+used.state.replaceAll('_',' ');details.append(p);}article.append(details);}
      check.onchange=()=>{if(check.checked&&selection.size>=limit){check.checked=false;status.textContent='Choose up to '+limit+' more files.';return;}if(check.checked)selection.set(asset.id,asset);else selection.delete(asset.id);dialog.querySelector('footer span').textContent=selection.size+' selected';use.disabled=busy||loading||!selection.size;};
      rows.append(article);
    }
    async function load(reset){
      if(busy)return;loading=true;use.disabled=true;
      const run=++serial;controller?.abort();controller=new AbortController();
      if(reset){rows.replaceChildren();cursor=null;dialog.querySelector('footer span').textContent=selection.size+' selected';}
      status.textContent='Loading saved media…';more.disabled=true;
      try{const query=new URLSearchParams({q:form.elements.q.value,kind:form.elements.kind.value});if(cursor)query.set('before',cursor);
        const response=await fetch('/api/media/library?'+query,{signal:controller.signal});const result=await response.json();
        if(!response.ok)throw new Error(typeof result.detail==='string'?result.detail:'Saved media could not load. Try again.');
        if(run!==serial||!dialog.open)return;result.assets.forEach(render);cursor=result.next_before;more.hidden=!cursor;status.textContent=rows.children.length?'':'No matching files. Upload from your device to get started.';
      }catch(error){if(error.name!=='AbortError'&&run===serial)status.textContent=error.message;}finally{if(run===serial){loading=false;more.disabled=busy;use.disabled=busy||!selection.size;}}
    }
    form.onsubmit=event=>{event.preventDefault();load(true);};more.onclick=()=>load(false);
    use.onclick=async()=>{if(busy||loading||!selection.size)return;if(workspace!==document.querySelector('meta[name=zova-workspace]')?.content){status.textContent='Workspace changed. Reopen saved media.';return;}
      busy=true;use.disabled=true;dialog.querySelectorAll('input,select,button').forEach(el=>el.disabled=true);
      try{await onSelect([...selection.values()]);busy=false;dialog.close();}catch(error){status.textContent=error.message;busy=false;dialog.querySelectorAll('input,select,button').forEach(el=>el.disabled=el.dataset.existing==='true');use.disabled=!selection.size;}
    };
    dialog.showModal();load(true);
  };
  document.addEventListener('DOMContentLoaded',()=>{
    const button=document.getElementById('studio-library');if(!button)return;
    button.onclick=()=>{
      if(mediaUploading||sendingMessage||!editableDraft())return;
      const version=mediaUploadVersion;
      window.zovaMediaLibrary({existing:uploadedMediaIds,limit:10-uploadedMediaIds.length,onSelect:async assets=>{
        if(version!==mediaUploadVersion||mediaUploading||sendingMessage||!editableDraft())throw new Error('This post changed. Close saved media and try again.');
        const selected=[...new Map([...uploadedMedia,...assets].map(a=>[a.id,a])).values()];
        if(selected.length>10 || (selected.some(a=>a.kind==='video')&&selected.length>1))throw new Error('Use one video or up to ten images per post.');
        uploadedMedia=selected;uploadedMediaIds=selected.map(a=>a.id);uploadedMediaKind=selected.some(a=>a.kind==='video')?'video':'image';uploadedVideoDuration=0;
        if(uploadedMediaKind==='video'){document.getElementById('px').checked=false;document.getElementById('pfb').checked=false;}
        renderAttachments();scheduleAutosave();await saveDraftNow();
      }});
    };
  });
})();
