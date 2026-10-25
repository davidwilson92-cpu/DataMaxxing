/* Keep provider handoffs as ordinary forms; only improve their waiting state. */
(() => {
  const forms = [...document.querySelectorAll('form[data-connection-form]')];
  let pending = false, activeForm = null, marker = null, status = null, timer = null, controls = [];
  function restore(message = '') {
    clearTimeout(timer); timer = null; pending = false;
    for (const saved of controls) {
      saved.button.disabled = saved.disabled;
      saved.button.textContent = saved.text;
    }
    controls = [];
    activeForm?.removeAttribute('aria-busy'); activeForm = null;
    marker?.remove(); marker = null;
    if (status) {
      if (message) { status.className = ''; status.textContent = message; }
      else { status.remove(); status = null; }
    }
  }
  for (const form of forms) form.addEventListener('submit', event => {
    if (pending) { event.preventDefault(); return; }
    if (event.defaultPrevented) return;
    status?.remove(); status = null;
    const submitter = event.submitter || form.querySelector('button[type="submit"],button:not([type])');
    // Disabled submit buttons are omitted from the form payload. Preserve the
    // selected route or cancel decision before disabling the visible controls.
    if (submitter?.name) {
      marker = document.createElement('input'); marker.type = 'hidden';
      marker.name = submitter.name; marker.value = submitter.value;
      form.appendChild(marker);
    }
    pending = true; activeForm = form; form.setAttribute('aria-busy', 'true');
    for (const other of forms) for (const button of other.querySelectorAll('button')) {
      controls.push({ button, disabled: button.disabled, text: button.textContent });
      button.disabled = true;
    }
    const message = submitter?.name === 'decision' ? 'Opening account options…' : 'Connecting…';
    if (submitter) submitter.textContent = message;
    status = document.createElement('p'); status.className = 'connection-status'; status.setAttribute('role', 'status');
    status.textContent = message; form.appendChild(status);
    // If navigation fails or is stopped, do not strand the user on disabled
    // controls. A repeated handoff is already protected by the server receipt.
    timer = setTimeout(() => restore('Connection didn’t open. Try again.'), 15000);
  });
  window.addEventListener('pagehide', () => clearTimeout(timer));
  window.addEventListener('pageshow', () => restore());
})();
