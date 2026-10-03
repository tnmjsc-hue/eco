import assert from 'node:assert/strict';
import { readFile, mkdir } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { createHash } from 'node:crypto';
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const url=process.argv[2]||'http://127.0.0.1:8876/';
const browser=await chromium.launch({headless:true,...(process.env.CHROME_EXECUTABLE?{executablePath:process.env.CHROME_EXECUTABLE}:{})});
await mkdir('test-results',{recursive:true});
try {
  const page=await browser.newPage({viewport:{width:1440,height:1000},acceptDownloads:true});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(url,{waitUntil:'networkidle'});
  await page.locator('#workspace').waitFor({state:'visible'});
  await page.locator('[data-mode="core"]').click();
  const coreScore=await page.locator('#score-value').innerText();
  await page.locator('[data-view="extended"]').click();
  await page.locator('#proxy-content').waitFor({state:'visible'});
  const pointer=await(await page.request.get(new URL('/data/network-proxies/latest.json',url).href)).json();
  const manifest=await(await page.request.get(new URL(pointer.manifest_url,url).href)).json();
  const history=await(await page.request.get(new URL(`/data/network-proxies/releases/${pointer.release_id}/history.json`,url).href)).json();
  assert.equal(await page.locator('#view-extended .proxy-card').count(),3);
  assert.equal(await page.locator('#proxy-date').inputValue(),manifest.last_observation_date);
  assert.equal(await page.locator('#proxy-results tr').count(),3);
  for (const [i,id] of ['exchange_share','address_activity','value_per_transfer'].entries()) {
    const value=history.rows.at(-1).metrics[id].score.toLocaleString('vi-VN',{minimumFractionDigits:1,maximumFractionDigits:1});
    assert.ok((await page.locator('.proxy-score').nth(i).innerText()).startsWith(value));
  }
  assert.ok((await page.locator('.proxy-card').first().innerText()).includes('flash'));
  const chart=await page.evaluate(()=>{
    const el=document.getElementById('proxy-chart');const c=echarts.getInstanceByDom(el);const canvas=el.querySelector('canvas');
    const data=canvas.getContext('2d').getImageData(0,0,canvas.width,canvas.height).data;let pixels=0;
    for(let i=3;i<data.length;i+=4)if(data[i])pixels++;
    return {pixels,series:c.getOption().series.map(s=>({name:s.name,n:s.data.length}))};
  });
  assert.ok(chart.pixels>1000);assert.equal(chart.series.length,3);
  assert.ok(chart.series.every(s=>s.n===history.rows.length));
  await page.locator('#proxy-date').fill('2015-07-30');await page.locator('#proxy-date').dispatchEvent('change');
  assert.ok((await page.locator('.proxy-score').allTextContents()).every(s=>s.startsWith('—')));
  await page.locator('#proxy-latest').focus();await page.locator('#proxy-latest').press('Enter');
  await page.locator('[data-proxy-range="1y"]').click();
  const lengths=await page.evaluate(()=>echarts.getInstanceByDom(document.getElementById('proxy-chart')).getOption().series.map(s=>s.data.length));
  assert.deepEqual(lengths,[366,366,366]);
  const downloadPromise=page.waitForEvent('download');await page.locator('#proxy-export').click();
  const text=await readFile(await(await downloadPromise).path(),'utf8');
  assert.ok(text.includes('CC BY-NC 4.0'));assert.ok(text.includes('exchange_share_score'));assert.equal(text.trim().split('\n').length,369);
  for(const width of [1440,768,390,360]) {
    await page.setViewportSize({width,height:900});await page.waitForTimeout(150);
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`proxy overflow ${width}`);
    await page.screenshot({path:`test-results/proxies-${width}.png`,fullPage:true});
  }
  const saved=await page.locator('.proxy-score').allTextContents();
  await page.route('**/data/network-proxies/latest.json',route=>route.abort());
  await page.locator('#proxy-refresh').click();await page.locator('#proxy-error').waitFor({state:'visible'});
  assert.deepEqual(await page.locator('.proxy-score').allTextContents(),saved);
  assert.ok((await page.locator('#proxy-error-text').innerText()).includes('giữ bản'));
  await page.unroute('**/data/network-proxies/latest.json');
  const historyUrl=`**/data/network-proxies/releases/${pointer.release_id}/history.json`;
  await page.route(historyUrl,route=>route.fulfill({body:'{"rows":[]}',contentType:'application/json'}));
  await page.locator('#proxy-retry').click();await page.waitForFunction(()=>document.getElementById('proxy-error-text').innerText.includes('Checksum'));
  assert.deepEqual(await page.locator('.proxy-score').allTextContents(),saved);
  await page.unroute(historyUrl);await page.locator('#proxy-retry').click();await page.locator('#proxy-error').waitFor({state:'hidden'});
  await page.locator('#proxy-date').fill('2020-01-01');await page.locator('#proxy-date').dispatchEvent('change');
  await page.locator('#proxy-refresh').click();await page.waitForFunction(()=>!document.getElementById('proxy-refresh').disabled);
  assert.equal(await page.locator('#proxy-date').inputValue(),'2020-01-01');
  await page.locator('[data-view="dashboard"]').click();await page.locator('[data-mode="core"]').click();assert.equal(await page.locator('#score-value').innerText(),coreScore);
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({url,proxy_release:pointer.release_id,metrics:3,calendar_rows:history.rows.length,
    viewport_checks:[1440,768,390,360],chart_nonblank_pixels:chart.pixels,csv:'366 days verified',
    null_warmup:'verified',network_and_checksum_failure:'preserves verified scores',historical_selection:'preserved',core_score:coreScore,page_errors:errors}));
} finally {await browser.close();}
