const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require('playwright');
const base = 'http://127.0.0.1:8784';
const out = path.resolve('docs/beta/evidence/20261025');

(async () => {
 const browser = await chromium.launch();
 try {
  const context = await browser.newContext({viewport:{width:390,height:760}});
  await context.route('**/*', r => r.request().url().startsWith(base+'/') ? r.continue() : r.abort());
  const page = await context.newPage();
  // Disposable local account, no provider connections and no AI requests.
  const signup = await context.request.post(base+'/signup',{form:{name:'Intro preview',email:`intro-${Date.now()}@example.test`,password:'Synthetic-intro-2026!',password_confirmation:'Synthetic-intro-2026!',accept_terms:'yes'}});
  assert.equal(signup.ok(),true);
  await page.goto(base+'/studio');
  await page.locator('#studioIntro[open]').waitFor();
  assert.equal(await page.locator('#introTitle').innerText(),'Start with an idea');
  assert.equal(await page.locator('#studioIntro .intro-count').innerText(),'1 of 3');
  for(let i=0;i<10;i++){
   await page.keyboard.press('Tab');
   assert.ok(await page.evaluate(()=>Boolean(document.activeElement.closest('#studioIntro'))),'Keyboard focus stays in the introduction');
  }
  fs.mkdirSync(out,{recursive:true});
  await page.screenshot({path:path.join(out,'studio-intro-first.png')});
  await page.locator('.intro-skip').click();
  assert.equal(await page.locator('#studioIntro').evaluate(el=>el.open),false);
  await page.reload();await page.waitForLoadState('networkidle');
  assert.equal(await page.locator('#studioIntro').evaluate(el=>el.open),false);
  assert.equal(await page.locator('#brief').inputValue(),'');

  // The same account on another device does not see another automatic tour.
  const other = await browser.newContext({storageState:await context.storageState()});
  const otherPage = await other.newPage();await otherPage.goto(base+'/studio');
  await otherPage.waitForLoadState('networkidle');
  assert.equal(await otherPage.locator('#studioIntro').evaluate(el=>el.open),false);
  await other.close();

  await page.getByRole('link',{name:'Guide',exact:true}).last().click();
  await page.getByRole('link',{name:'Show me around Studio'}).click();
  await page.locator('#studioIntro[open]').waitFor();
  assert.equal(new URL(page.url()).searchParams.has('intro'),false);
  for (const [width,height] of [[320,568],[390,500],[844,390],[1440,900]]) {
   await page.setViewportSize({width,height});
   for (let step=0;step<3;step++) {
    const box=await page.locator('.intro-bubble').boundingBox();
    assert.ok(box.x>=0&&box.y>=0&&box.x+box.width<=width+1&&box.y+box.height<=height+1,`Tip fits ${width}x${height}: ${JSON.stringify(box)}`);
    assert.equal(await page.locator('.intro-skip').isVisible(),true);
    assert.ok((await page.locator('.intro-next').boundingBox()).height>=44);
    if(step<2)await page.locator('.intro-next').click();
   }
   await page.screenshot({path:path.join(out,`studio-intro-${width}.png`)});
   await page.locator('.intro-back').click();await page.locator('.intro-back').click();
  }
  await page.locator('.intro-next').click();await page.locator('.intro-next').click();await page.locator('.intro-next').click();
  assert.equal(await page.locator('#studioIntro').evaluate(el=>el.open),false);
  // Closing does not focus a text field or change the user's work.
  assert.equal(await page.locator('#brief').inputValue(),'');
  assert.notEqual(await page.evaluate(()=>document.activeElement.tagName),'TEXTAREA');
  await page.goto(base+'/studio?intro=1');await page.locator('#studioIntro[open]').waitFor();
  await page.keyboard.press('Escape');
  assert.equal(await page.locator('#studioIntro').evaluate(el=>el.open),false);

  await page.setViewportSize({width:390,height:844});
  await page.goto(base+'/');
  assert.match(await page.locator('.flow-copy h1').innerText(),/Because content\s+is the fun part\./);
  assert.equal(await page.locator('.flow-copy>p').innerText(),'Turn your ideas into captions and a content plan with Zova, your AI social media manager.');
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  await page.screenshot({path:path.join(out,'landing-content-fun-mobile.png')});
  await page.goto(base+'/guide');await page.screenshot({path:path.join(out,'guide-mobile.png'),fullPage:true});
  console.log('Studio intro: first visit, skip, account persistence, replay, completion, Escape, viewport and landing checks passed');
 } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exit(1);});
