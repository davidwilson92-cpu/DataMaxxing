const assert = require('node:assert/strict');
const {chromium} = require('playwright');

(async () => {
  const browser = await chromium.launch({headless: true});
  try {
    const page = await browser.newPage({viewport: {width: 390, height: 844}});
    await page.goto('http://127.0.0.1:8784/signup');
    const email = page.locator('input[type="email"]');
    await email.fill('creator@domain');
    assert.equal(await email.evaluate(e => e.checkValidity()), false);
    await email.fill('creator@example.test');
    assert.equal(await email.evaluate(e => e.checkValidity()), true);
    const passwords = page.locator('input[autocomplete="new-password"]');
    assert.equal(await passwords.count(), 2);
    await passwords.nth(0).fill('synthetic-only-123');
    await passwords.nth(1).fill('different-only-123');
    assert.equal(await passwords.nth(1).evaluate(e => e.checkValidity()), false);
    await passwords.nth(1).fill('synthetic-only-123');
    assert.equal(await passwords.nth(1).evaluate(e => e.checkValidity()), true);
    const visibility = page.locator('.password-visibility').first();
    await visibility.click();
    assert.equal(await passwords.nth(0).getAttribute('type'), 'text');
    await visibility.click();
    assert.equal(await passwords.nth(0).getAttribute('type'), 'password');
    assert.match(await page.locator('.password-guidance').innerText(), /✓ 10–256 characters · ✓ Passwords match/);
    assert.equal(await page.locator('body').evaluate(e => e.scrollWidth > window.innerWidth), false);
    console.log('Account fields: complete email, separate visibility, matching passwords and mobile layout passed.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
