// Ask once before AI processing. The server independently enforces the saved choice.
(() => {
  const fetchOriginal = window.fetch.bind(window);
  let permission = false, pending = null;
  const usesAI = path => path.startsWith('/api/ai/') || path.startsWith('/api/voice/') ||
    ['/api/conversation/plan','/api/insights','/api/strategy/propose','/api/strategy/recommend'].includes(path) ||
    /^\/api\/(strategy\/actions|series\/occurrences)\/[^/]+\/draft$/.test(path);
  const read = async (url, options) => {
    const response = await fetchOriginal(url, options);
    const data = await response.json();
    if (!response.ok) throw new Error('Your privacy choice could not be saved. Try again.');
    return data;
  };
  async function choose() {
    const state = await read('/api/privacy/ai');
    if (state.allowed || !state.required) { permission = true; return true; }
    const dialog = document.getElementById('aiPrivacyDialog');
    if (!dialog) return false;
    return new Promise(resolve => {
      const error = dialog.querySelector('[role="status"]');
      const allow = dialog.querySelector('[data-ai-allow]');
      const cancel = dialog.querySelector('[data-ai-cancel]');
      let saving = false;
      error.textContent = ''; allow.disabled = false; cancel.disabled = false;
      const closed = () => { cleanup(); resolve(false); };
      const cancelPending = event => { if (saving) event.preventDefault(); };
      const cleanup = () => {
        dialog.removeEventListener('close', closed);
        dialog.removeEventListener('cancel', cancelPending);
        allow.onclick = null; cancel.onclick = null;
      };
      dialog.addEventListener('close', closed, {once:true});
      dialog.addEventListener('cancel', cancelPending);
      cancel.onclick = () => dialog.close();
      allow.onclick = async () => {
        saving = true; allow.disabled = true; cancel.disabled = true;
        try {
          await read('/api/privacy/ai', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({allowed:true,version:state.version})});
          permission = true;
          cleanup(); dialog.close(); resolve(true);
        } catch (err) { saving = false; error.textContent = err.message; allow.disabled = false; cancel.disabled = false; }
      };
      dialog.showModal();
      cancel.focus();
    });
  }
  async function ensure() {
    if (permission) return true;
    if (!pending) pending = choose().finally(() => { pending = null; });
    return pending;
  }
  window.fetch = async (input, init = {}) => {
    const url = new URL(input instanceof Request ? input.url : input, location.href);
    const method = (init.method || (input instanceof Request ? input.method : 'GET')).toUpperCase();
    const ai = method === 'POST' && url.origin === location.origin && usesAI(url.pathname);
    if (ai && !await ensure()) return new Response(JSON.stringify({detail:'AI was not used. Your message is kept so you can continue later.'}),{status:403,headers:{'Content-Type':'application/json'}});
    const response = await fetchOriginal(input, init);
    if (ai && response.status === 403) permission = false;
    return response;
  };
  document.addEventListener('DOMContentLoaded', async () => {
    const button = document.getElementById('aiPrivacyChoice');
    if (!button) return;
    const note = document.getElementById('aiPrivacyStatus');
    async function refresh() {
      const state = await read('/api/privacy/ai');
      permission = state.allowed;
      button.textContent = state.allowed ? 'Turn off AI sharing' : 'Review AI sharing';
      note.textContent = state.allowed ? 'AI sharing is on. You choose when to use it.' : 'AI sharing is off. You can still edit and manage saved work.';
      return state;
    }
    button.onclick = async () => {
      button.disabled = true;
      try {
        const state = await read('/api/privacy/ai');
        if (state.allowed) {
          await read('/api/privacy/ai',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({allowed:false,version:state.version})});
          permission = false;
        } else await ensure();
        await refresh();
      } catch (err) { note.textContent = err.message; }
      finally { button.disabled = false; button.focus(); }
    };
    try { await refresh(); } catch (err) { note.textContent = err.message; }
  });
})();
