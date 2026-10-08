import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {mkdir} from 'node:fs/promises';
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const url=process.argv[2]||'http://127.0.0.1:8877/';
await mkdir('test-results',{recursive:true});
const browser=await chromium.launch({headless:true,...(process.env.CHROME_EXECUTABLE?{executablePath:process.env.CHROME_EXECUTABLE}:{})});
try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[],providerRequests=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(/bls\.gov|bea\.gov|federalreserve\.gov|r2\.cloudflarestorage/.test(r.url()))providerRequests.push(r.url());});
  await page.addInitScript(()=>{if(window===top)localStorage.setItem('eco-language','vi');});
  await page.goto(`${url.split('#')[0]}#calendar`,{waitUntil:'networkidle'});
  await page.locator('#macro-content').waitFor({state:'visible'});
  assert.equal(await page.locator('#macro-error').isVisible(),false,await page.locator('#macro-error').textContent());
  assert.equal(await page.locator('#cal-error').isVisible(),false);
  assert.equal(await page.locator('#cal-indicators article').count(),5);
  assert.equal(await page.locator('#macro-assets article').count(),3);
  assert.equal(await page.locator('#macro-axes>div').count(),3);
  const identity=await page.locator('#macro-content').getAttribute('data-assessment-id');
  const context=await page.locator('#macro-regime').innerText();
  const latest=await page.locator('#macro-latest-title').innerText();
  await page.locator('[data-cal-range="past"]').click();
  await page.locator('#cal-search').fill('CPI');
  assert.equal(await page.locator('#macro-latest-title').innerText(),latest);
  assert.equal(await page.locator('#macro-regime').innerText(),context);
  assert.equal(await page.locator('.usd-bullish,.usd-bearish').count(),0);
  await page.locator('#cal-zone').selectOption('America/New_York');
  assert.equal(await page.locator('#macro-content').getAttribute('data-assessment-id'),identity);
  await page.locator('#cal-search').fill('');
  await page.locator('#cal-zone').selectOption('Asia/Ho_Chi_Minh');
  await page.locator('.macro-peers>summary').click();
  assert.ok(await page.locator('#macro-peers tr').count()>=7);
  await page.locator('.macro-details>summary').click();
  assert.ok((await page.locator('#macro-rules').innerText()).includes('X10_NO_CONSENSUS'));
  assert.ok((await page.locator('#macro-provenance').innerText()).includes(identity));
  assert.ok((await page.locator('#macro-manifest').getAttribute('href')).includes('/manifest.json'));
  await page.locator('.macro-details>summary').click();
  await page.locator('.macro-peers>summary').click();
  for(const language of ['en','ko','ru','hi','tr','pt-BR','en-NG','vi']){
    await page.locator('#language-picker').selectOption(language);
    assert.equal(await page.locator('#macro-content').getAttribute('data-assessment-id'),identity);
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,`locale ${language}`);
    if(language==='en'){
      const text=await page.locator('#macro-content').innerText();
      assert.ok(text.includes('Compared with the previous period'));assert.ok(!/[ăđơư]/i.test(text),text);
    }
  }
  for(const width of [1440,768,390,360]){
    await page.setViewportSize({width,height:1000});
    await page.screenshot({path:`test-results/macro-${width}.png`,fullPage:true});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,`width ${width}`);
  }
  const preserved=await page.locator('#macro-date').innerText();
  await page.route('**/data/macro-assessment/latest.json',r=>r.abort());
  await page.locator('#cal-refresh').click();await page.locator('#macro-error').waitFor({state:'visible'});
  assert.equal(await page.locator('#macro-date').innerText(),preserved);
  assert.equal(await page.locator('#macro-content').getAttribute('data-assessment-id'),identity);
  assert.equal(await page.locator('#macro-assets .insufficient_evidence').count(),3);
  await page.unroute('**/data/macro-assessment/latest.json');
  await page.locator('#cal-refresh').click();await page.locator('#macro-error').waitFor({state:'hidden'});
  await page.route('**/data/macro-assessment/releases/*/assessment.json',async r=>{const res=await r.fetch();const data=await res.json();data.assets.usd.conclusion='supportive';await r.fulfill({json:data});});
  await page.locator('#cal-refresh').click();await page.locator('#macro-error').waitFor({state:'visible'});
  assert.equal(await page.locator('#macro-content').getAttribute('data-assessment-id'),identity);
  await page.unroute('**/data/macro-assessment/releases/*/assessment.json');
  await page.locator('#cal-refresh').click();await page.locator('#macro-error').waitFor({state:'hidden'});
  await page.route('**/data/calendar/latest.json',r=>r.abort());
  await page.locator('#cal-refresh').click();await page.locator('#cal-error').waitFor({state:'visible'});
  assert.equal(await page.locator('#macro-content').getAttribute('data-assessment-id'),identity);
  await page.unroute('**/data/calendar/latest.json');
  await page.locator('#cal-retry').click();await page.locator('#cal-error').waitFor({state:'hidden'});
  await page.locator('[data-view="dashboard"]').click();await page.locator('#score-value').waitFor({state:'visible'});
  assert.ok(Number((await page.locator('#score-value').innerText()).replace(',','.'))>0);
  const chart=await page.evaluate(()=>echarts.getInstanceByDom(document.getElementById('history-chart')).getOption().series.map(s=>s.name));
  assert.deepEqual(chart,['Core 10','Giá ETH']);
  await page.locator('[data-view="calendar"]').click();
  assert.equal(await page.locator('#macro-content').getAttribute('data-assessment-id'),identity);
  assert.deepEqual(errors,[]);assert.deepEqual(providerRequests,[]);
  console.log(JSON.stringify({calendar_macro_browser_verified:true,url,assessment_id:identity,viewports:[1440,768,390,360],languages:8,source_requests:0,filter_invariance:true,retained_date:true,checksum_guard:true,dashboard_regression:true}));
}finally{await browser.close();}
