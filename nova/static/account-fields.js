// Progressive enhancement only: server validation remains authoritative.
document.querySelectorAll('input[type="email"]').forEach(input => {
  input.addEventListener('input', () => {
    input.setCustomValidity(input.value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(input.value.trim()) ? 'Enter a complete email address, such as you@example.com.' : '');
  });
});
const passwordEye = hidden => `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>${hidden?'<path d="m3 3 18 18"/>':''}</svg>`;
document.querySelectorAll('input[type="password"]').forEach(input => {
  const wrap = document.createElement('div'); wrap.className = 'password-field';
  input.before(wrap); wrap.append(input);
  const button = document.createElement('button'); button.type = 'button';
  button.className = 'password-visibility'; button.innerHTML = passwordEye(false);
  button.setAttribute('aria-controls', input.id); button.setAttribute('aria-pressed', 'false');
  button.setAttribute('aria-label', 'Show ' + (document.querySelector(`label[for="${input.id}"]`)?.textContent || 'password').toLowerCase());
  button.addEventListener('click', () => {
    const show = input.type === 'password'; input.type = show ? 'text' : 'password';
    button.innerHTML = passwordEye(show); button.setAttribute('aria-pressed', String(show));
    button.setAttribute('aria-label', (show ? 'Hide ' : 'Show ') + (document.querySelector(`label[for="${input.id}"]`)?.textContent || 'password').toLowerCase());
  }); wrap.append(button);
});
document.querySelectorAll('form').forEach(form => {
  const fields = [...form.querySelectorAll('input[autocomplete="new-password"]')];
  if (fields.length !== 2) return;
  const [password, confirm] = fields;
  password.maxLength = 256; confirm.maxLength = 256;
  const hints = document.createElement('p'); hints.className = 'password-guidance';
  hints.id = password.id + '-guidance'; password.setAttribute('aria-describedby', hints.id);
  confirm.setAttribute('aria-describedby', hints.id); confirm.parentElement.after(hints);
  const update = () => {
    const length = password.value.length >= 10 && password.value.length <= 256;
    const matches = !!confirm.value && password.value === confirm.value;
    hints.textContent = `${length ? '✓' : '○'} 10–256 characters · ${matches ? '✓' : '○'} Passwords match`;
    confirm.setCustomValidity(confirm.value && !matches ? 'Passwords do not match.' : '');
  };
  password.addEventListener('input', update); confirm.addEventListener('input', update); update();
});
