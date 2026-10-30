(() => {
  if (!['/studio', '/account'].includes(location.pathname)) return;
  let checking = false, last = 0;
  async function check() {
    if (document.hidden || checking || Date.now()-last < 60000) return;
    checking = true; last = Date.now();
    try {
      const reply = await fetch('/api/connections/check', {method:'POST', headers:{'Content-Type':'application/json'}, body:'{}'});
      if (!reply.ok) return;
      const data = await reply.json(), rows = Array.isArray(data.connections) ? data.connections : [];
      const reconnect = rows.filter(row => row.status === 'reconnect');
      let banner = document.getElementById('connectionHealthNotice');
      if (!banner) {
        const host = document.querySelector('.conversation-stage, .account-flow');
        if (!host) return;
        banner = document.createElement('aside'); banner.id = 'connectionHealthNotice'; banner.className = 'account-notice'; banner.setAttribute('role','status'); host.prepend(banner);
      }
      banner.replaceChildren(); banner.hidden = !reconnect.length;
      if (reconnect.length) {
        const names = {instagram:'Instagram', facebook:'Facebook', tiktok:'TikTok', x:'X'};
        const label = document.createElement('p'); label.textContent = 'Reconnect ' + [...new Set(reconnect.map(row => names[row.platform]).filter(Boolean))].join(', ') + '. Access has expired or been removed. Your drafts are safe.'; banner.append(label);
        for (const platform of new Set(reconnect.map(row => row.platform))) {
          if (!names[platform]) continue;
          const link = document.createElement('a'); link.href = window.zovaWorkspaceUrl?.('/connect/'+platform) || '/connect/'+platform; link.textContent = 'Reconnect '+names[platform]; link.className = 'button ghost'; banner.append(link);
        }
      }
      rows.forEach(row => {
        const state = document.querySelector(`[data-connection-id="${Number(row.id)}"] .connection-state`);
        if (state) state.textContent = row.status === 'reconnect' ? 'Reconnect needed' : row.status === 'unavailable' ? 'Check unavailable' : 'Connected';
      });
    } catch (_) { /* Keep previous status on a transport failure. */ }
    finally { checking = false; }
  }
  check(); window.addEventListener('focus', check); document.addEventListener('visibilitychange', check); setInterval(check, 60000);
})();
