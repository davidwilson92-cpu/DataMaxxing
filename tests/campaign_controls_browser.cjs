const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
(async () => {
  const browser = await chromium.launch();
  try {
    for (const [persona,width] of [390,1366].entries()) {
      const page = await browser.newPage({viewport:{width,height:844},locale:'en-GB',timezoneId:'Europe/London'});
      page.setDefaultTimeout(10000);
      const errors=[];page.on('pageerror',e=>errors.push(e.message));
      await page.goto('http://127.0.0.1:8797/fixture/'+persona);
      await page.locator('#campaign-form').getByLabel('Campaign name',{exact:true}).fill('Friday flowers');
      await page.getByLabel('What are you promoting?').fill('Friday bouquet collection at our Brixton florist.');
      await page.locator('#campaign-form').getByLabel('First post').fill('2027-01-08');
      await page.getByLabel('Instagram',{exact:true}).check();
      await page.getByLabel('Facebook',{exact:true}).check();
      await page.getByLabel('Total posts').fill('2');
      await page.getByRole('button',{name:'Build campaign',exact:true}).click();
      const cards=page.locator('#campaign-posts article');await cards.first().waitFor();
      const original=await cards.first().locator('p').first().innerText();
      const toolbar=page.locator('.campaign-command-panel');
      assert((await toolbar.boundingBox()).height<=140,'Campaign controls must remain compact');
      assert.equal(await page.locator('body').evaluate(el=>getComputedStyle(el).backgroundColor),'rgb(255, 255, 255)');
      await page.locator('#campaign-tools summary').click();
      await page.getByRole('button',{name:'Reuse campaign',exact:true}).focus();
      await page.keyboard.press('Escape');
      assert.equal(await page.locator('#campaign-tools').getAttribute('open'),null);
      const control=page.locator('#campaign-control-form');
      async function tool(name){await page.locator('#campaign-tools summary').click();await page.getByRole('button',{name,exact:true}).click();await control.waitFor({state:'visible'});}
      async function submit(){await page.locator('#campaign-control-submit').click();await control.waitFor({state:'hidden'});}
      // Cancel a local post edit; secondary actions must become usable again.
      await cards.first().locator('.post-actions summary').click();
      await cards.first().getByLabel('Caption',{exact:true}).fill('Do not save this edit');
      await cards.first().getByRole('button',{name:'Cancel',exact:true}).click();
      assert.equal(await cards.first().locator('p').first().innerText(),original);
      await tool('Pause campaign');await control.getByRole('button',{name:'Cancel',exact:true}).click();
      assert.equal(await page.locator('#campaign-state').innerText(),'');
      await tool('Pause campaign');await submit();await page.getByText('Paused · drafts kept',{exact:true}).waitFor();
      await tool('Resume campaign');await submit();assert.equal(await page.locator('#campaign-state').innerText(),'');
      await tool('Move remaining dates');await control.locator('[name=new_start]').fill('2027-02-01T12:00');await submit();
      assert.match(await cards.first().locator('time').getAttribute('datetime'),/^2027-02-01T12:00/);
      await page.getByRole('button',{name:'Save posts to Schedule',exact:true}).click();await page.getByText('Open in Studio',{exact:true}).first().waitFor();
      await page.getByRole('button',{name:'Improve remaining posts',exact:true}).click();await control.waitFor({state:'visible'});
      await control.locator('[name=feedback]').fill('Make it welcoming and local.');
      await page.getByLabel('Sort by').selectOption('platform');
      assert.equal(await control.locator('[name=feedback]').inputValue(),'Make it welcoming and local.');
      await page.getByLabel('Sort by').selectOption('date');await submit();
      const proposal=page.locator('#campaign-suggestion');await proposal.waitFor({state:'visible'});
      assert.equal(await cards.first().locator('p').first().innerText(),original);
      const originals=proposal.locator('details').filter({has:page.locator('summary',{hasText:'Original caption'})});
      await originals.first().locator('summary').click();assert.equal(await originals.first().locator('p').innerText(),original);
      // Saved preview survives refresh and explicit campaign reopening.
      await page.reload();await page.getByLabel('Saved campaigns').selectOption({label:'Friday flowers'});await proposal.waitFor({state:'visible'});
      await page.getByRole('button',{name:'Keep originals',exact:true}).click();await proposal.waitFor({state:'hidden'});
      assert.equal(await cards.first().locator('p').first().innerText(),original);
      await page.getByRole('button',{name:'Improve remaining posts',exact:true}).click();await control.waitFor({state:'visible'});await submit();await proposal.waitFor({state:'visible'});
      await page.getByRole('button',{name:'Apply changes',exact:true}).click();await proposal.waitFor({state:'hidden'});
      assert.notEqual(await cards.first().locator('p').first().innerText(),original);
      // The request succeeds server-side but its response is lost; retry must reuse the same copy.
      await tool('Reuse campaign');await control.locator('[name=copy_name]').fill('Spring flowers');await control.locator('[name=new_start]').fill('2027-04-01T12:00');
      let lost=false;
      await page.route('**/api/campaigns/*/reuse',async route=>{if(!lost){lost=true;await route.fetch();await route.abort('failed');}else await route.continue();});
      await page.locator('#campaign-control-submit').click();await page.waitForFunction(()=>document.querySelector('#campaign-status').textContent.includes('fetch'));
      await submit();await page.getByRole('heading',{name:'Spring flowers',exact:true}).waitFor();
      assert.equal(await page.getByLabel('Saved campaigns').locator('option').count(),3);
      await tool('Add posts');await control.locator('[name=new_start]').fill('2027-05-01T12:00');await submit();await proposal.waitFor({state:'visible'});
      await page.getByRole('button',{name:'Apply changes',exact:true}).click();await proposal.waitFor({state:'hidden'});assert.equal(await cards.count(),4);
      await page.getByLabel('View',{exact:true}).selectOption('calendar');assert(await page.locator('.calendar-marks').count()>0);
      await page.getByLabel('View',{exact:true}).selectOption('list');await page.getByLabel('Sort by').selectOption('platform');
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
      assert.deepEqual(errors,[]);
      if(process.env.ZOVA_SCREENSHOTS){fs.mkdirSync(process.env.ZOVA_SCREENSHOTS,{recursive:true});await page.screenshot({path:process.env.ZOVA_SCREENSHOTS+'/campaign-controls-'+width+'.png',fullPage:true});}
      // A completed campaign has no Improve button; cancelling reuse still restores keyboard focus.
      await page.route(/\/api\/campaigns\/\d+$/,async route=>{
        const response=await route.fetch(),row=await response.json();
        row.posts.forEach(post=>post.status='published');
        await route.fulfill({response,json:row});
      });
      await page.reload();await page.getByLabel('Saved campaigns').selectOption({label:'Spring flowers'});
      await page.locator('#improve-remaining').waitFor({state:'hidden'});
      await tool('Reuse campaign');await control.getByRole('button',{name:'Cancel',exact:true}).click();
      assert.equal(await page.locator('#campaign-tools summary').evaluate(el=>el===document.activeElement),true);
      console.log(width+': create, cancel, pause/resume, move, save, improve/discard/apply, reload, lost-response reuse, extend and calendar passed');
      await page.close();
    }
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exit(1);});
