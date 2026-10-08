import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
const hash = b => createHash('sha256').update(b).digest('hex');
const pointer = await readFile('public/data/calendar/latest.json');
const status = await readFile('public/data/calendar/status.json');
const data = JSON.parse(pointer);
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
    console.log(JSON.stringify({production_verified:true,release_id:data.release_id})); process.exit(0);
  } catch { /* CDN may still serve the previous release. */ }
}
throw Error('Production calendar did not match the verified artifacts');
