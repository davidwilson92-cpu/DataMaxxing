// Browser regression against tests/strategy_preview.py only. Start that isolated
// fixture, then run with Playwright available via NODE_PATH. No post is sent.
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const base = 'http://127.0.0.1:8784';

async function visibleAction(page, selector, height) {
  const result = await page.locator(selector).evaluate(el => {
    const box = el.getBoundingClientRect();
    const unobscured = [box.y + 2, box.y + box.height / 2, box.bottom - 2].every(y => {
      const hit = document.elementFromPoint(box.x + box.width / 2, y);
      return hit === el || el.contains(hit);
    });
    return { top: box.top, bottom: box.bottom, height: box.height, hit: unobscured };
  });
  assert.ok(result.top >= 0 && result.bottom <= height + 1, `${selector} stays in visible viewport: ${JSON.stringify(result)}`);
  assert.ok(result.height >= 44, `${selector} retains a 44px target`);
  assert.ok(result.hit, `${selector} is not covered by another control`);
}

(async () => {
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
    await page.route('**/*', route => route.request().url().startsWith(base + '/') ? route.continue() : route.abort());
    await page.goto(base + '/login');
    await page.locator('#email').fill('strategy@example.test');
    await page.locator('#password').fill('Synthetic-preview-2026!');
    await page.locator('button[type=submit]').click();
    await page.waitForURL('**/studio');
    // Account health may refresh in the background; readiness is the composer,
    // not the absence of all network traffic.
    await page.locator('#brief').waitFor({state:'visible'});
    assert.equal(await page.locator('.composer-platforms input:checked').count(), 4);

    for (const height of [844, 500, 350]) {
      await page.setViewportSize({ width: 390, height });
      await page.locator('#brief').focus();
      await page.waitForFunction(height => document.querySelector('.conversation-workspace').getBoundingClientRect().height === height, height);
      for (const attached of [false, true]) {
        // Synthetic DOM media tests the real layout without uploading user files.
        await page.evaluate(attached => {
          const tray = document.getElementById('attachmentTray');
          tray.classList.toggle('hidden', !attached);
          tray.innerHTML = attached ? '<article class="attachment-card"><div class="attachment-details"><span>sample.jpg</span><button type="button">Remove</button></div></article>' : '';
          document.getElementById('groundingNotice').hidden = !attached;
          document.querySelector('.chat-composer').scrollTop = 0;
        }, attached);
        await page.locator('#brief').fill(attached ? 'A long description of my next post. '.repeat(25) : 'Draft my next post');
        await visibleAction(page, '#brief', height);
        await visibleAction(page, '#generateBtn', height);
        assert.equal(await page.locator('.welcome-message:visible').count(), 0, 'Typing retains the blank canvas');
        const contentFits = await page.locator('.chat-composer').evaluate(el => el.scrollHeight <= el.clientHeight + 1);
        if (contentFits) {
          for (const selector of ['#threadLength', '#instagramFormatControl label:first-of-type', '#instagramFormatControl label:last-child']) {
            await visibleAction(page, selector, height);
          }
        }
        for (const selector of ['#threadLength', '#instagramFormatControl label:last-child', ...(attached ? ['.attachment-details button'] : [])]) {
          await page.locator(selector).evaluate(el => el.scrollIntoView({ block: 'center' }));
          await visibleAction(page, selector, height);
          await visibleAction(page, '#brief', height);
          await visibleAction(page, '#generateBtn', height);
        }
        const scroll = await page.evaluate(() => ({ doc: document.documentElement.scrollWidth, width: innerWidth }));
        assert.ok(scroll.doc <= scroll.width, 'No horizontal page overflow');
      }
    }

    // iOS can shrink only visualViewport while layout viewport remains tall.
    await page.setViewportSize({ width: 390, height: 844 });
    await page.waitForFunction(() => document.querySelector('.conversation-workspace').getBoundingClientRect().height === 844);
    await page.evaluate(() => document.querySelector('.conversation-workspace').style.setProperty('--chat-height', '350px'));
    await visibleAction(page, '#brief', 350);
    await visibleAction(page, '#generateBtn', 350);
    console.log('PASS: mobile composer at 390×844, 390×500, 390×350 and a short visual viewport; all four platforms, long text, attachments, format controls and 44px Send.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
