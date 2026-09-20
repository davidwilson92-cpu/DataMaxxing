// Pin each rendered page to its workspace, including requests from older tabs.
(() => {
  const workspace = document.querySelector('meta[name="zova-workspace"]')?.content;
  if (workspace === undefined) return;
  window.zovaWorkspaceUrl = path => {
    const url=new URL(path,location.href);url.searchParams.set('workspace',workspace);
    return url.pathname+url.search+url.hash;
  };
  const originalFetch = window.fetch.bind(window);
  window.fetch = (input, init = {}) => {
    const url = new URL(input instanceof Request ? input.url : input, location.href);
    if (url.origin === location.origin) {
      const headers = new Headers(init.headers || (input instanceof Request ? input.headers : undefined));
      headers.set('X-Zova-Brand', workspace);
      init = {...init, headers};
    }
    return originalFetch(input, init);
  };
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('a[href]').forEach(link => {
      const url = new URL(link.href, location.href);
      if (url.origin === location.origin && !url.pathname.startsWith('/billing/')) {
        url.searchParams.set('workspace', workspace); link.href = url.href;
      }
    });
    document.querySelectorAll('form').forEach(form => {
      const url = new URL(form.action, location.href);
      if (url.origin === location.origin) {
        url.searchParams.set('workspace', workspace); form.action = url.href;
      }
    });
  });
  document.addEventListener('click', event => {
    const link=event.target.closest('a[href]');
    if(link && new URL(link.href,location.href).origin===location.origin) link.href=window.zovaWorkspaceUrl(link.href);
  },true);
})();
