(() => {
  'use strict';

  for (const form of document.querySelectorAll('form[data-security-form]')) {
    const button = form.querySelector('button[type="submit"]');
    const message = form.querySelector('[data-security-message]');
    let pending = false;

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      if (pending || !form.reportValidity()) return;

      const action = new URL(form.action, location.href);
      if (action.origin !== location.origin || form.method.toUpperCase() !== 'POST') {
        message.textContent = 'Open this form directly in Zova and try again.';
        return;
      }

      pending = true;
      button.disabled = true;
      form.setAttribute('aria-busy', 'true');
      message.textContent = 'Please wait…';
      let leaving = false;
      let failure = 'The request could not be completed. Your entries are still here; please try again.';

      try {
        // Native HTML POSTs under no-referrer have an opaque Origin. CORS-mode
        // fetch keeps the real Origin even for this same-origin request, while
        // no-referrer still keeps security links out of Referer headers.
        // The server's existing origin checks remain unchanged.
        const response = await fetch(action.href, {
          method: 'POST',
          mode: 'cors',
          credentials: 'same-origin',
          referrerPolicy: 'no-referrer',
          body: new FormData(form),
        });

        if (!response.ok) {
          try {
            const body = await response.json();
            if (typeof body.detail === 'string') failure = body.detail.slice(0, 300);
          } catch (_) {
            // Never display a raw server response, request body or credential.
          }
          throw new Error('Request rejected');
        }

        const destination = new URL(response.url || action.href, location.href);
        if (destination.origin !== location.origin) throw new Error('Unexpected destination');
        location.assign(destination.href);
        leaving = true;
      } catch (_) {
        message.textContent = failure;
      } finally {
        if (!leaving) {
          pending = false;
          button.disabled = false;
          form.removeAttribute('aria-busy');
        }
      }
    });
  }
})();
