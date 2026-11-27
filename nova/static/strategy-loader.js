/* Load planning code when the creator opens it; retain every existing entry point. */
(() => {
  const source = document.currentScript.dataset.source;
  let pending;
  function load() {
    if (pending) return pending;
    pending = new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = source;
      script.onload = resolve;
      script.onerror = () => {
        script.remove();
        pending = undefined;
        reject(new Error('Next move could not load. Please try again.'));
      };
      document.head.append(script);
    });
    return pending;
  }
  for (const name of ['openNextMove', 'openSeriesPanel', 'openSeriesBuilder']) {
    const open = async (...args) => {
      const button = document.activeElement;
      button?.setAttribute('aria-busy', 'true');
      try {
        await load();
        return window[name](...args);
      } catch (error) {
        document.getElementById('undoStatus').textContent = error.message;
      } finally {
        button?.removeAttribute('aria-busy');
      }
    };
    window[name] = open;
  }
  function initialRoute() {
    const query = new URLSearchParams(location.search);
    if (query.get('strategy') === '1') window.openNextMove(true);
    else if (query.get('series') === '1') window.openSeriesPanel();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initialRoute, {once: true});
  else initialRoute();
})();
