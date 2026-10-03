import assert from 'node:assert/strict';
import { readFile, mkdir } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { createHash } from 'node:crypto';
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const url=process.argv[2]||'http://127.0.0.1:8876/';
const browser=await chromium.launch({headless:true,...(process.env.CHROME_EXECUTABLE?{executablePath:process.env.CHROME_EXECUTABLE}:{})});
await mkdir('test-results',{recursive:true});
const ids=['nupl_diagnostic','supply_change_30d','exchange_balance_change_30d'];
const sha=b=>createHash('sha256').update(b).digest('hex');
try {
  const page=await browser.newPage({viewport:{width:1440,height:1000},acceptDownloads:true});await page.clock.install({time:new Date()});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(new URL('#diagnostics',url).href,{waitUntil:'networkidle'});await page.locator('#diag-content').waitFor({state:'visible'});
  const pointer=await(await page.request.get(new URL('/data/diagnostics/latest.json',url).href)).json();
  const manifest=await(await page.request.get(new URL(pointer.manifest_url,url).href)).json();
  const history=await(await page.request.get(new URL(`/data/diagnostics/releases/${pointer.release_id}/history.json`,url).href)).json();
  assert.equal(await page.locator('.diagnostic-card').count(),3);assert.equal(await page.locator('#diag-date').inputValue(),history.rows.at(-1).date);
  assert.equal(await page.locator('#diag-coverage tr').count(),3);
  const last=history.rows.at(-1);
  for(const [i,id] of ids.entries()) {
    const expected=(last.metrics[id].value*(i===0?100:1)).toLocaleString('vi-VN',{minimumFractionDigits:i===2?0:3,maximumFractionDigits:i===2?0:3});
    assert.ok((await page.locator('.diag-value').nth(i).innerText()).startsWith(expected));
  }
  assert.ok((await page.locator('.diagnostic-card').nth(2).innerText()).includes('flash'));
  const chartState=()=>page.evaluate(()=>{
    const el=document.getElementById('diag-chart'),chart=echarts.getInstanceByDom(el),canvas=el.querySelector('canvas');
    const pixels=canvas.getContext('2d').getImageData(0,0,canvas.width,canvas.height).data;let count=0;for(let i=3;i<pixels.length;i+=4)if(pixels[i])count++;
    return {pixels:count,option:chart.getOption()};
  });
  let chart=await chartState();assert.ok(chart.pixels>1000);assert.equal(chart.option.series.length,1);assert.equal(chart.option.series[0].data.length,history.rows.length);
  assert.ok(chart.option.series[0].data.some(p=>p[1]<0));assert.equal(chart.option.series[0].connectNulls,false);
  await page.locator('#diag-date').fill(history.rows[0].date);await page.locator('#diag-date').dispatchEvent('change');
  assert.ok((await page.locator('.diag-value').allTextContents()).every(t=>t==='—'));
  assert.ok((await page.locator('.diagnostic-card').nth(1).innerText()).includes('31 ngày'));
  const historical=history.rows[1000].date;await page.locator('#diag-date').fill(historical);await page.locator('#diag-date').dispatchEvent('change');
  await page.locator('#diag-refresh').click();await page.waitForFunction(()=>!document.getElementById('diag-refresh').disabled);
  assert.equal(await page.locator('#diag-date').inputValue(),historical);
  await page.locator('#diag-latest').focus();await page.locator('#diag-latest').press('Enter');
  await page.locator('#diag-metric').selectOption(ids[2]);await page.locator('[data-diag-range="1y"]').click();
  chart=await chartState();assert.equal(chart.option.series[0].data.length,366);assert.equal(chart.option.yAxis[0].name,'ETH');
  let downloadPromise=page.waitForEvent('download');await page.locator('#diag-export').click();
  let csv=await readFile(await(await downloadPromise).path(),'utf8');assert.equal(csv.trim().split('\n').length,369);assert.ok(csv.includes(String(last.metrics[ids[2]].value)));
  await page.locator('#diag-start').fill('2024-01-01');await page.locator('#diag-end').fill('2024-01-05');await page.locator('#diag-apply').focus();await page.locator('#diag-apply').press('Enter');
  assert.equal((await chartState()).option.series[0].data.length,5);
  downloadPromise=page.waitForEvent('download');await page.locator('#diag-export').click();csv=await readFile(await(await downloadPromise).path(),'utf8');assert.equal(csv.trim().split('\n').length,8);assert.ok(csv.includes('2024-01-01'));assert.ok(!csv.includes('2024-01-06'));
  await page.locator('#diag-start').fill('2024-01-06');await page.locator('#diag-apply').click();await page.locator('#diag-range-error').waitFor({state:'visible'});
  assert.equal((await chartState()).option.series[0].data.length,5);
  await page.locator('[data-diag-range="all"]').click();await page.locator('#diag-metric').selectOption(ids[0]);
  for(const width of [1440,768,390,360]) {
    await page.setViewportSize({width,height:1000});await page.waitForTimeout(150);
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`diagnostic overflow ${width}`);
    assert.ok((await chartState()).pixels>1000);
    await page.screenshot({path:`test-results/diagnostics-${width}.png`,fullPage:true});
  }
  const saved=await page.locator('.diag-value').allTextContents();
  await page.route('**/data/diagnostics/latest.json',r=>r.abort());await page.locator('#diag-refresh').click();await page.locator('#diag-error').waitFor({state:'visible'});
  assert.deepEqual(await page.locator('.diag-value').allTextContents(),saved);assert.ok((await page.locator('#diag-error-text').innerText()).includes('giữ bản'));
  await page.unroute('**/data/diagnostics/latest.json');
  const historyUrl=`**/data/diagnostics/releases/${pointer.release_id}/history.json`;
  await page.route(historyUrl,r=>r.fulfill({body:'{"rows":[]}',contentType:'application/json'}));await page.locator('#diag-retry').click();
  await page.waitForFunction(()=>document.getElementById('diag-error-text').innerText.includes('Checksum'));assert.deepEqual(await page.locator('.diag-value').allTextContents(),saved);
  await page.unroute(historyUrl);await page.locator('#diag-retry').click();await page.waitForFunction(()=>!document.getElementById('diag-refresh').disabled && document.getElementById('diag-error').hidden);
  await page.route('**/data/diagnostics/latest.json',r=>r.fulfill({body:JSON.stringify({...pointer,manifest_sha256:'f'.repeat(64)}),contentType:'application/json'}));
  await page.locator('#diag-refresh').click();await page.waitForFunction(()=>document.getElementById('diag-error-text').innerText.includes('bị thay đổi'));
  assert.deepEqual(await page.locator('.diag-value').allTextContents(),saved);await page.unroute('**/data/diagnostics/latest.json');
  const advanced=structuredClone(history),tomorrow=new Date(Date.parse(last.date)+86400000).toISOString().slice(0,10),nextID='diagnostic-'+'e'.repeat(20);
  advanced.release_id=nextID;
  advanced.rows.push({...structuredClone(last),date:tomorrow});const hb=JSON.stringify(advanced)+'\n';
  // Reuse model fixtures to produce a fully valid forward publication for refresh behavior.
  const report=JSON.parse(await(await page.request.get(new URL(`/data/diagnostics/releases/${pointer.release_id}/research.json`,url).href)).text());
  const summarize=rows=>Object.fromEntries(ids.map(id=>{const valid=rows.filter(r=>r.metrics[id].value!==null),values=valid.map(r=>r.metrics[id].value);return [id,{valid_rows:valid.length,null_rows:rows.length-valid.length,first_valid_date:valid[0]?.date??null,last_valid_date:valid.at(-1)?.date??null,last_value:values.at(-1)??null,minimum:Math.min(...values),maximum:Math.max(...values),negative_rows:values.filter(v=>v<0).length,zero_rows:values.filter(v=>v===0).length,flagged_rows:rows.filter(r=>r.metrics[id].source_flags.length).length}];}));
  report.coverage=summarize(advanced.rows);const post=advanced.rows.filter(r=>r.date>='2024-03-13');report.regimes.post_dencun={rows:post.length,metrics:summarize(post)};
  const rb=JSON.stringify(report)+'\n',nextManifest={...manifest,release_id:nextID,rows:advanced.rows.length,last_observation_date:tomorrow,coverage:report.coverage,files:{'history.json':sha(hb),'research.json':sha(rb)}};
  const mb=JSON.stringify(nextManifest)+'\n',nextPointer={...pointer,release_id:nextID,manifest_url:`/data/diagnostics/releases/${nextID}/manifest.json`,manifest_sha256:sha(mb)};
  for(const [path,body] of [['/data/diagnostics/latest.json',JSON.stringify(nextPointer)], [nextPointer.manifest_url,mb], [`/data/diagnostics/releases/${nextID}/history.json`,hb], [`/data/diagnostics/releases/${nextID}/research.json`,rb]]) await page.route('**'+path,r=>r.fulfill({body,contentType:'application/json'}));
  await page.locator('#diag-date').fill(historical);await page.locator('#diag-date').dispatchEvent('change');
  await page.clock.fastForward(15*60*1000);await page.waitForFunction(d=>document.getElementById('diag-date').max===d,tomorrow);
  assert.equal(await page.locator('#diag-date').inputValue(),historical);
  await page.locator('#diag-latest').click();assert.equal(await page.locator('#diag-date').inputValue(),tomorrow);
  assert.deepEqual(errors,[]);console.log(JSON.stringify({diagnostics_ui:'PASS',release_id:pointer.release_id,viewports:[1440,768,390,360],checks:['signed units','nulls','chart','calendar CSV','keyboard','retry','checksum retention','auto refresh','historical selection']}));
}finally {await browser.close();}
