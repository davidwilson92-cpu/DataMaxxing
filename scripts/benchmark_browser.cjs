// Production pages on the disposable benchmark server, in an isolated browser profile.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const {chromium} = require('playwright');
const base = process.argv[2];
const output = process.argv[3];
if (!/^http:\/\/127\.0\.0\.1:\d+$/.test(base)) throw Error('Loopback benchmark only');

(async () => {
  const browser = await chromium.launch(process.env.BENCH_EDGE ? {channel: 'msedge'} : {});
  const result = {viewport: {width:390,height:844}, network:{latency_ms:70,download_bytes_s:500000,upload_bytes_s:250000}, cpu_slowdown:4, runs:[], errors:[]};
  try {
    const context = await browser.newContext({viewport:result.viewport});
    const page = await context.newPage();
    const cdp = await context.newCDPSession(page);
    await cdp.send('Network.enable');
    await cdp.send('Network.emulateNetworkConditions', {offline:false,latency:result.network.latency_ms,
      downloadThroughput:result.network.download_bytes_s,uploadThroughput:result.network.upload_bytes_s});
    await cdp.send('Emulation.setCPUThrottlingRate', {rate:result.cpu_slowdown});
    page.on('pageerror', error => result.errors.push(error.message));
    await page.addInitScript(() => {
      window.benchmarkPaints = {longTasks:[],largestContentfulPaint:0};
      new PerformanceObserver(list => list.getEntries().forEach(entry => {
        window.benchmarkPaints.longTasks.push(entry.duration);
      })).observe({type:'longtask',buffered:true});
      new PerformanceObserver(list => list.getEntries().forEach(entry => {
        window.benchmarkPaints.largestContentfulPaint = entry.startTime;
      })).observe({type:'largest-contentful-paint',buffered:true});
    });
    async function capture(name, elapsed) {
      await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
      result.runs.push({name,interaction_ms:Math.round(elapsed*100)/100,...await page.evaluate(() => ({
        fcp_ms:performance.getEntriesByName('first-contentful-paint')[0]?.startTime,
        lcp_ms:window.benchmarkPaints.largestContentfulPaint,
        dom_ready_ms:performance.getEntriesByType('navigation')[0].domContentLoadedEventEnd,
        long_tasks_ms:window.benchmarkPaints.longTasks,
        resources:performance.getEntriesByType('resource').map(r => ({
          path:new URL(r.name).pathname,ms:r.duration,bytes:r.encodedBodySize,transfer:r.transferSize,
          kind:r.initiatorType,blocking:r.renderBlockingStatus
        }))
      }))});
    }
    let started=performance.now();
    await page.goto(base+'/login');
    await page.locator('#email').waitFor();
    await capture('login_page',performance.now()-started);
    await page.locator('#email').fill('benchmark@example.test');
    await page.locator('#password').fill('Synthetic-benchmark-only-2026!');
    started=performance.now();
    await page.locator('button[type=submit]').click();
    await page.waitForURL('**/studio');
    await page.locator('#brief').waitFor();
    await capture('login_to_composer',performance.now()-started);
    await page.locator('.recent-posts a').first().waitFor({state:'attached'});
    await capture('studio_history_ready',performance.now()-started);
    for (let i=0;i<3;i++) {
      started=performance.now();
      await page.goto(base+'/studio');
      await page.locator('.recent-posts a').first().waitFor({state:'attached'});
      await capture('studio_repeat_'+i,performance.now()-started);
    }
    started=performance.now();
    await page.locator('.next-move-launch').click();
    await page.locator('#strategyActions .move-hero').first().waitFor();
    await capture('next_move_open',performance.now()-started);
    const previous = await page.locator('#strategyActions .move-hero h3').innerText();
    started=performance.now();
    await page.locator('#recommendButton').click();
    await page.waitForFunction(text => document.querySelector('#strategyActions .move-hero h3')?.textContent !== text, previous);
    await page.waitForFunction(() => document.querySelector('#strategyPanel')?.getAttribute('aria-busy') === 'false');
    await capture('next_move_fresh',performance.now()-started);
    await page.locator('#strategyClose').click();
    started=performance.now();
    await page.goto(base+'/analytics');
    await page.locator('#analyticsNote').filter({hasText:'Checked'}).waitFor();
    await capture('performance_ready',performance.now()-started);
    started=performance.now();
    await page.locator('#analyticsWindow').selectOption('30');
    await page.locator('#analyticsRefresh').waitFor({state:'visible'});
    await page.waitForFunction(() => !document.getElementById('analyticsRefresh').disabled);
    await capture('performance_window_change',performance.now()-started);
    started=performance.now();
    await page.goto(base+'/drafts');
    await page.locator('#scheduleCalendar [data-schedule-day]').first().waitFor();
    await capture('schedule_ready',performance.now()-started);
    fs.mkdirSync(path.dirname(output),{recursive:true});
    await page.screenshot({path:output.replace(/\.json$/,'.png')});
    assert.deepEqual(result.errors,[]);
  } finally {
    fs.mkdirSync(path.dirname(output),{recursive:true});
    fs.writeFileSync(output,JSON.stringify(result,null,2)+'\n');
    await browser.close();
  }
})().catch(error=>{console.error(error);process.exitCode=1;});
