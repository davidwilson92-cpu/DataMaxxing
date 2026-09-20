document.addEventListener('DOMContentLoaded', () => {
  const input = document.getElementById('mediaInput');
  const tray = document.getElementById('attachmentTray');
  const notice = document.getElementById('groundingNotice');
  const update = () => { if (notice) notice.hidden = !(tray && tray.children.length); };
  if (input) input.addEventListener('change', () => { if (notice && input.files.length) notice.hidden = false; });
  if (tray) new MutationObserver(update).observe(tray, {childList:true});
  update();
  if (document.querySelector('meta[name="zova-product-metrics"]')) {
    const wrap = document.createElement('div');
    const button = document.createElement('button');
    button.className = 'quiet-button'; button.type = 'button'; button.textContent = 'This draft is useful';
    const status = document.createElement('p'); status.setAttribute('role','status');
    status.textContent = 'Optional feedback records a milestone, not your text.';
    wrap.className = 'support-note';
    wrap.append(button, status); document.getElementById('postSettings').append(wrap);
    const showFeedback = () => { wrap.hidden = !document.getElementById('draftResponse'); };
    new MutationObserver(showFeedback).observe(document.getElementById('chatFeed'),{childList:true});
    showFeedback();
    button.addEventListener('click', async () => {
      const id = currentDraftId;
      if (!id) { status.textContent = 'Create a draft version first.'; return; }
      button.disabled = true;
      try {
        await saveDraftNow();
        if (id !== currentDraftId) return;
        await api('/api/drafts/' + id + '/useful', {method:'POST'});
        if (id === currentDraftId) status.textContent = 'Thank you. Your feedback was recorded.';
      } catch (error) { if (id === currentDraftId) status.textContent = error.message; }
      finally { button.disabled = false; }
    });
  }
});

function contextualRefinements() {
  if (!editableDraft()) return;
  const host = document.querySelector('#draftResponse .draft-options > div');
  if (!host || host.querySelector('[data-contextual-edit]')) return;
  const text = (variants[currentPlatform]?.posts || []).join(' ');
  const day = text.match(/\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b/i)?.[0];
  if (!day) return;
  const button = document.createElement('button');
  button.type = 'button'; button.dataset.contextualEdit = 'true';
  button.textContent = 'Lead with ' + day;
  button.addEventListener('click', () => promptComposer('Revise only the ' + platformName(currentPlatform) + ' version: lead with the existing reference to ' + day + '. Keep the facts and call to action; do not add new claims.'));
  host.append(button);
}
