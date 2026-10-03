import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';

const hash = body => createHash('sha256').update(body).digest('hex');
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const expectedStatus = await readFile('public/data/status.json');
const expectedPointer = await readFile('public/data/latest.json');
const expectedProxyPointer = await readFile('public/data/network-proxies/latest.json');
const expectedProxyStatus = await readFile('public/data/network-proxies/status.json');
const expectedExtendedPointer = await readFile('public/data/extended/latest.json');
const expectedExtendedStatus = await readFile('public/data/extended/status.json');
const hook = process.env.CLOUDFLARE_DEPLOY_HOOK;
if (!hook || new URL(hook).hostname !== 'api.cloudflare.com') throw new Error('Missing or unexpected Cloudflare deployment hook.');
try {
  const response = await fetch(hook, { method: 'POST', signal: AbortSignal.timeout(30000) });
  if (!response.ok) throw new Error('hook');
  await response.body?.cancel();
} catch { throw new Error('Cloudflare deployment hook failed; inspect Pages without exposing the hook URL.'); }

async function bytes(path) {
  const response = await fetch(`https://eco.tnmp.cloud${path}`, { cache: 'no-store', signal: AbortSignal.timeout(20000) });
  if (!response.ok) throw new Error('Production response unavailable');
  return Buffer.from(await response.arrayBuffer());
}
let verified = false;
for (let attempt = 0; attempt < 40; attempt++) {
  await sleep(10000);
  try {
    if (hash(await bytes('/data/status.json')) !== hash(expectedStatus)
        || hash(await bytes('/data/latest.json')) !== hash(expectedPointer)) continue;
    const pointer = JSON.parse(expectedPointer);
    const manifestBytes = await bytes(pointer.manifest_url);
    if (hash(manifestBytes) !== pointer.manifest_sha256) continue;
    const manifest = JSON.parse(manifestBytes);
    for (const [file, sha] of Object.entries(manifest.files)) {
      if (!['history.json', 'research.json'].includes(file)) throw new Error('Unexpected public artifact');
      if (hash(await bytes(`/data/releases/${pointer.release_id}/${file}`)) !== sha) throw new Error('Production checksum mismatch');
    }
    if (hash(await bytes('/data/network-proxies/latest.json')) !== hash(expectedProxyPointer)
        || hash(await bytes('/data/network-proxies/status.json')) !== hash(expectedProxyStatus)) continue;
    const proxy = JSON.parse(expectedProxyPointer);
    if (!/^proxy-[a-f0-9]{20}$/.test(proxy.release_id)
        || proxy.manifest_url !== `/data/network-proxies/releases/${proxy.release_id}/manifest.json`) throw new Error('Invalid proxy pointer');
    const proxyManifestBytes = await bytes(proxy.manifest_url);
    if (hash(proxyManifestBytes) !== proxy.manifest_sha256) continue;
    const proxyManifest = JSON.parse(proxyManifestBytes);
    for (const [file, sha] of Object.entries(proxyManifest.files)) {
      if (!['history.json','research.json'].includes(file)) throw new Error('Unexpected proxy artifact');
      if (hash(await bytes(`/data/network-proxies/releases/${proxy.release_id}/${file}`)) !== sha) throw new Error('Proxy checksum mismatch');
    }
    if (hash(await bytes('/data/extended/latest.json')) !== hash(expectedExtendedPointer)
        || hash(await bytes('/data/extended/status.json')) !== hash(expectedExtendedStatus)) continue;
    const extended = JSON.parse(expectedExtendedPointer);
    if (!/^extended-[a-f0-9]{20}$/.test(extended.release_id)
        || extended.manifest_url !== `/data/extended/releases/${extended.release_id}/manifest.json`) throw new Error('Invalid Extended pointer');
    const extendedBytes = await bytes(extended.manifest_url);
    if (hash(extendedBytes) !== extended.manifest_sha256) continue;
    const extendedManifest = JSON.parse(extendedBytes);
    for (const [file,sha] of Object.entries(extendedManifest.files)) {
      if (!['history.json','research.json'].includes(file)) throw new Error('Unexpected Extended artifact');
      if (hash(await bytes(`/data/extended/releases/${extended.release_id}/${file}`)) !== sha) throw new Error('Extended checksum mismatch');
    }
    verified = true;
    console.log(JSON.stringify({ production_verified: true, release_id: pointer.release_id, proxy_release_id: proxy.release_id, extended_release_id:extended.release_id }));
    break;
  } catch { /* Keep waiting for the complete new deployment, never accept a mixed release. */ }
}
if (!verified) throw new Error('Production verification timed out; retain artifacts and inspect Pages deployment.');
