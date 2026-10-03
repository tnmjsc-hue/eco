import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';

const hash = body => createHash('sha256').update(body).digest('hex');
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const expectedStatus = await readFile('public/data/status.json');
const expectedPointer = await readFile('public/data/latest.json');
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
    verified = true;
    console.log(JSON.stringify({ production_verified: true, release_id: pointer.release_id }));
    break;
  } catch { /* Keep waiting for the complete new deployment, never accept a mixed release. */ }
}
if (!verified) throw new Error('Production verification timed out; retain artifacts and inspect Pages deployment.');
