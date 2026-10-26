/* One account-level introduction; no AI calls and no changes to a user's work. */
(() => {
  const dialog = document.getElementById('studioIntro');
  if (!dialog) return;
  const config = JSON.parse(document.getElementById('studioIntroConfig').textContent);
  const bubble = dialog.querySelector('.intro-bubble'), highlight = dialog.querySelector('.intro-highlight');
  const next = dialog.querySelector('.intro-next'), back = dialog.querySelector('.intro-back');
  const paths = [
    '<path d="m14 4 6 6M4 20l4-1 12-12a2.8 2.8 0 0 0-4-4L4 15v5Z"/>',
    '<circle cx="6" cy="12" r="3"/><circle cx="18" cy="5" r="3"/><circle cx="18" cy="19" r="3"/><path d="m9 10 6-4M9 14l6 4"/>',
    '<path d="m12 2 2.5 7.5L22 12l-7.5 2.5L12 22l-2.5-7.5L2 12l7.5-2.5Z"/>'
  ];
  const steps = [
    {target:'#brief', title:'Start with an idea', text:'Type what you want to post. Use + to add photos or video.'},
    {target:'.composer-platforms', title:'Choose your socials', text:'Tap your platforms. Edit Zova’s caption, then publish or schedule. You approve every post.'},
    {target:'.next-move-launch', title:'Need an idea?', text:'Tap Next move. Add Your strategy for ideas that fit your goals.'}
  ];
  let step = 0, previousFocus, interacted = false;
  window.addEventListener('pointerdown',() => {interacted = true;},{once:true,capture:true});
  window.addEventListener('keydown',() => {interacted = true;},{once:true,capture:true});
  function position() {
    if (!dialog.open) return;
    const target = document.querySelector(steps[step].target);
    if (!target) { dialog.close(); return; }
    const rect = target.getBoundingClientRect(), width = window.innerWidth, height = window.visualViewport?.height || window.innerHeight;
    const left = Math.max(8, rect.left - 5), top = Math.max(8, rect.top - 5);
    const right = Math.min(width - 8, rect.right + 5), bottom = Math.min(height - 8, rect.bottom + 5);
    Object.assign(highlight.style, {left:left+'px',top:top+'px',width:Math.max(0,right-left)+'px',height:Math.max(0,bottom-top)+'px'});
    const box = bubble.getBoundingClientRect(), x = Math.max(16, Math.min(width-box.width-16, (left+right-box.width)/2));
    const below = bottom + 16 + box.height <= height - 12;
    const y = Math.max(12, Math.min(height-box.height-12, below ? bottom+16 : top-box.height-16));
    bubble.dataset.side = below ? 'below' : 'above';
    bubble.style.left = x+'px'; bubble.style.top = y+'px';
    bubble.style.setProperty('--tip-x',Math.max(24,Math.min(box.width-36,(left+right)/2-x))+'px');
  }
  function render() {
    dialog.querySelector('.intro-count').textContent = `${step+1} of ${steps.length}`;
    dialog.querySelector('.intro-icon').innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${paths[step]}</svg>`;
    dialog.querySelector('h2').textContent = steps[step].title;
    dialog.querySelector('p').textContent = steps[step].text;
    back.hidden = step === 0;
    next.textContent = step === steps.length-1 ? 'Let’s create' : 'Next →';
    position(); next.focus({preventScroll:true});
  }
  next.addEventListener('click',() => { if(step === steps.length-1) dialog.close(); else {step++;render();} });
  back.addEventListener('click',() => {if(step>0){step--;render();} });
  dialog.querySelector('.intro-skip').addEventListener('click',() => dialog.close());
  dialog.addEventListener('keydown',event => {
    if(event.key !== 'Tab') return;
    const controls = [...dialog.querySelectorAll('button,a[href]')].filter(el => !el.disabled && !el.hidden && el.getClientRects().length);
    const first = controls[0], last = controls[controls.length-1];
    if(event.shiftKey && document.activeElement === first){event.preventDefault();last?.focus();}
    else if(!event.shiftKey && document.activeElement === last){event.preventDefault();first?.focus();}
  });
  dialog.addEventListener('close',() => {
    window.removeEventListener('resize',position);window.visualViewport?.removeEventListener('resize',position);
    // Do not summon the keyboard just because an introduction ended.
    const focus = previousFocus && previousFocus !== document.body && !previousFocus.matches('input,textarea') ? previousFocus : document.getElementById('newChatBtn');
    focus?.focus({preventScroll:true});
  });
  window.addEventListener('zova:studio-ready',async () => {
    const query = new URLSearchParams(location.search), manual = query.get('intro') === '1';
    if (!config.pending && !manual) return;
    try {
      const response = await fetch('/api/studio/intro/claim',{method:'POST',credentials:'same-origin'});
      if (!response.ok) return;
      const state = await response.json();
      if (!manual && (!state.show || query.has('draft') || query.has('strategy') || query.has('series'))) return;
      if (!manual && interacted) return;
      if (document.querySelector('dialog[open]') || document.activeElement?.matches('input,textarea')) return;
      // Remove only the replay instruction; preserve the user's workspace/query.
      if(manual){query.delete('intro');history.replaceState({},'',location.pathname+(query.size?'?'+query.toString():'')+location.hash);}
      previousFocus = document.activeElement; render(); dialog.showModal(); position(); next.focus({preventScroll:true});
      window.addEventListener('resize',position);window.visualViewport?.addEventListener('resize',position);
    } catch (_) { /* An intro must never prevent creating a post. */ }
  },{once:true});
})();
