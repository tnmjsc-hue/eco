import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
const hash = b => createHash('sha256').update(b).digest('hex');
const pointer = await readFile('public/data/calendar/latest.json');
const status = await readFile('public/data/calendar/status.json');
const data = JSON.parse(pointer);
const macroPointer=await readFile('public/data/macro-assessment/latest.json');
const macroStatus=await readFile('public/data/macro-assessment/status.json');
const macro=JSON.parse(macroPointer);
const manifestBytes=await readFile(`public${macro.manifest.url}`);
if(hash(manifestBytes)!==macro.manifest.sha256)throw Error('Invalid macro manifest');
const manifest=JSON.parse(manifestBytes);
const macroAssets=[macro,macro.manifest,...['calendar','observations','batch_status','ruleset'].map(k=>manifest[k])];
const currentMacroStatus=JSON.parse(macroStatus);if(currentMacroStatus.batch_status)macroAssets.push(currentMacroStatus.batch_status);
const probabilityPointer=await readFile('public/data/macro-probability/latest.json');
const probabilityStatus=await readFile('public/data/macro-probability/status.json');
const probability=JSON.parse(probabilityPointer);
const probabilityManifestBytes=await readFile(`public${probability.manifest.url}`);
if(hash(probabilityManifestBytes)!==probability.manifest.sha256)throw Error('Invalid probability manifest');
const probabilityManifest=JSON.parse(probabilityManifestBytes);
const probabilityInputs=JSON.parse(await readFile(`public${probabilityManifest.inputs.url}`));
const probabilityAssets=[probability,probability.manifest,probabilityManifest.inputs,probabilityManifest.protocol,...probabilityInputs.cases,...probabilityInputs.outcomes,...Object.values(probabilityInputs.macro_parents),...Object.values(probabilityInputs.eth_parent)];
for(const a of probabilityAssets){if(!/^\/data\/(?:macro-probability\/(?:records\/case-[a-f0-9]{20}|outcomes\/result-[a-f0-9]{20}|releases\/prob-[a-f0-9]{20}\/(?:report|manifest|inputs|protocol))|(?:calendar|macro-assessment)\/[a-zA-Z0-9/.-]+|core-v2\/releases\/core10-[a-f0-9]{20}\/(?:manifest|history))\.json$/.test(a.url)||hash(await readFile(`public${a.url}`))!==a.sha256)throw Error('Invalid probability asset');}
const marketPointer=await readFile('public/data/macro-market/latest.json');
const marketStatus=await readFile('public/data/macro-market/status.json');
const market=JSON.parse(marketPointer);
const marketManifestBytes=await readFile(`public${market.manifest.url}`);
if(hash(marketManifestBytes)!==market.manifest.sha256)throw Error('Invalid market manifest');
const marketManifest=JSON.parse(marketManifestBytes);
const marketAssets=[market,market.manifest,marketManifest.inputs,marketManifest.protocol,marketManifest.eth_parent.manifest,marketManifest.eth_parent.history];
for(const a of marketAssets){if(!/^\/data\/(?:macro-market\/releases\/market-[a-f0-9]{20}\/(?:market|manifest|inputs|protocol)|core-v2\/releases\/core10-[a-f0-9]{20}\/(?:manifest|history))\.json$/.test(a.url)||hash(await readFile(`public${a.url}`))!==a.sha256)throw Error('Invalid market asset');}
for(const asset of macroAssets){if(!/^\/data\/(calendar|macro-assessment)\/[a-zA-Z0-9/.-]+\.json$/.test(asset.url)||hash(await readFile(`public${asset.url}`))!==asset.sha256)throw Error('Invalid macro asset');}
if (!/^calendar-[a-f0-9]{20}$/.test(data.release_id) || data.url !== `/data/calendar/releases/${data.release_id}/calendar.json`) throw Error('Invalid calendar pointer');
const hook = process.env.CLOUDFLARE_DEPLOY_HOOK;
if (!hook || new URL(hook).hostname !== 'api.cloudflare.com') throw Error('Missing approved Pages deployment hook');
try { const r = await fetch(hook, {method:'POST',signal:AbortSignal.timeout(30000)}); if (!r.ok) throw Error(); await r.body?.cancel(); }
catch { throw Error('Pages deployment hook failed'); }
for (let attempt = 0; attempt < 40; attempt++) {
  await new Promise(resolve => setTimeout(resolve,10000));
  try {
    const bytes = async path => { const r=await fetch(`https://eco.tnmp.cloud${path}`,{cache:'no-store',signal:AbortSignal.timeout(15000)}); if (!r.ok) throw Error(); return Buffer.from(await r.arrayBuffer()); };
    if (hash(await bytes('/data/calendar/latest.json')) !== hash(pointer) || hash(await bytes('/data/calendar/status.json')) !== hash(status) || hash(await bytes(data.url)) !== data.sha256) continue;
    if(hash(await bytes('/data/macro-assessment/latest.json'))!==hash(macroPointer)||hash(await bytes('/data/macro-assessment/status.json'))!==hash(macroStatus))continue;
    const checks=await Promise.all(macroAssets.map(async a=>hash(await bytes(a.url))===a.sha256));if(!checks.every(Boolean))continue;
    if(hash(await bytes('/data/macro-market/latest.json'))!==hash(marketPointer)||hash(await bytes('/data/macro-market/status.json'))!==hash(marketStatus))continue;
    if(!(await Promise.all(marketAssets.map(async a=>hash(await bytes(a.url))===a.sha256))).every(Boolean))continue;
    if(hash(await bytes('/data/macro-probability/latest.json'))!==hash(probabilityPointer)||hash(await bytes('/data/macro-probability/status.json'))!==hash(probabilityStatus))continue;
    if(!(await Promise.all(probabilityAssets.map(async a=>hash(await bytes(a.url))===a.sha256))).every(Boolean))continue;
    console.log(JSON.stringify({production_verified:true,release_id:data.release_id,assessment_id:macro.assessment_id,macro_assets_verified:macroAssets.length,market_release_id:market.release_id,market_assets_verified:marketAssets.length,probability_release_id:probability.release_id,probability_assets_verified:probabilityAssets.length})); process.exit(0);
  } catch { /* CDN may still serve the previous release. */ }
}
throw Error('Production calendar did not match the verified artifacts');
