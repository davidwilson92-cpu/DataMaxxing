const assert=require('node:assert/strict');
const {chromium}=require('playwright');
const path=require('node:path');
const fs=require('node:fs');
const base='http://127.0.0.1:8784';
(async()=>{
 const browser=await chromium.launch();
 try{
  const page=await browser.newPage({viewport:{width:390,height:760}});
  await page.route('**/*',route=>route.request().url().startsWith(base+'/')?route.continue():route.abort());
  await page.goto(base+'/login');await page.locator('#email').fill('strategy@example.test');await page.locator('#password').fill('Synthetic-preview-2026!');await page.locator('button[type=submit]').click();await page.waitForURL('**/studio');
  await page.goto(base+'/studio?strategy=1');await page.locator('#strategyBrief').waitFor({state:'visible'});
  assert.equal(await page.locator('#nextMoveSettings textarea').count(),2);
  await page.locator('#strategyBrief').fill('I run a pottery studio for local beginners. Help me fill weekend classes.');
  await page.locator('#strategyDirection').fill('');
  await page.getByRole('button',{name:'Behind the scenes',exact:true}).click();
  await page.getByRole('button',{name:'Helpful tips',exact:true}).click();
  const direction=await page.locator('#strategyDirection').inputValue();
  assert.equal(direction,'Behind the scenes · Helpful tips');
  const out=path.resolve('docs/beta/evidence/20261025');fs.mkdirSync(out,{recursive:true});
  await page.screenshot({path:path.join(out,'strategy-two-boxes.png')});
  await page.locator('#buildStrategyButton').click();
  // Consent, when requested by the existing account policy, remains explicit.
  const consent=page.getByRole('button',{name:'Allow AI assistance',exact:true});
  if(await consent.isVisible())await consent.click();
  await page.locator('#saveStrategyButton').waitFor({state:'visible'});
  await page.locator('#saveStrategyButton').click();await page.locator('#strategyNextMoveButton').waitFor({state:'visible'});
  await page.reload();await page.locator('#strategyBrief').waitFor({state:'visible'});
  assert.match(await page.locator('#strategyBrief').inputValue(),/pottery studio/);
  assert.equal(await page.locator('#strategyDirection').inputValue(),direction);
  await page.locator('#strategyDirection').fill('Only one photo a week. No videos.');
  assert.equal(await page.locator('#strategyForm').isVisible(),false);
  await page.locator('#buildStrategyButton').click();await page.locator('#saveStrategyButton').click();await page.locator('#strategyNextMoveButton').click();
  await page.locator('.move-hero h3').waitFor({state:'visible'});
  assert.equal(await page.locator('.move-recommendation h4').innerText(),'✦ AI recommendation');
  assert.equal(await page.getByText('Change this idea',{exact:true}).count(),0);
  assert.equal(await page.getByText('Details',{exact:true}).count(),0);
  assert.equal(await page.locator('#strategyEditLink').isVisible(),true);
  for(const height of [760,650]){
   await page.setViewportSize({width:390,height});
   await page.screenshot({path:path.join(out,`next-move-focused-${height}.png`)});
   const bounds=await page.locator('#strategyEditLink').boundingBox();
   assert.ok(bounds.y>=0&&bounds.y+bounds.height<=height,`Strategy callout fits: ${JSON.stringify(bounds)}`);
   assert.ok(await page.locator('#strategyPanel').evaluate(el=>el.scrollWidth<=el.clientWidth+1),'No horizontal overflow');
  }
  let requestCount=0;page.on('request',r=>{if(r.url().endsWith('/api/strategy/recommend'))requestCount++;});
  const first=await page.locator('.move-hero h3').innerText();
  for(let i=0;i<2;i++)await page.getByRole('button',{name:'Next idea',exact:true}).click();
  assert.equal(requestCount,0);
  await page.getByRole('button',{name:'Next idea',exact:true}).click();
  await page.getByText('Idea 4',{exact:true}).waitFor();assert.equal(requestCount,1);
  assert.notEqual(await page.locator('.move-hero h3').innerText(),first);
  await page.screenshot({path:path.join(out,'next-move-fresh-batch.png')});
  await page.getByRole('button',{name:'Draft post',exact:false}).click();await page.waitForURL(/draft=/);
  assert.ok(await page.locator('#chatFeed').innerText());
  console.log('PASS: two inputs, suggestions, save/reload/edit, consistent recommendation, 650/760 layout, fresh fourth idea, one-click draft');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
