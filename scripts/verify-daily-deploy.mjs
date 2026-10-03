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
const expectedDiagnosticPointer = await readFile('public/data/diagnostics/latest.json');
const expectedDiagnosticStatus = await readFile('public/data/diagnostics/status.json');
const expectedCoreTenPointer = await readFile('public/data/core-v2/latest.json');
const expectedCoreTenStatus = await readFile('public/data/core-v2/status.json');
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
    if (hash(await bytes('/data/diagnostics/latest.json')) !== hash(expectedDiagnosticPointer)
        || hash(await bytes('/data/diagnostics/status.json')) !== hash(expectedDiagnosticStatus)) continue;
    const diagnostic=JSON.parse(expectedDiagnosticPointer);
    if (!/^diagnostic-[a-f0-9]{20}$/.test(diagnostic.release_id)
        || diagnostic.manifest_url!==`/data/diagnostics/releases/${diagnostic.release_id}/manifest.json`) throw new Error('Invalid diagnostic pointer');
    const diagnosticBytes=await bytes(diagnostic.manifest_url);
    if (hash(diagnosticBytes)!==diagnostic.manifest_sha256) continue;
    const diagnosticManifest=JSON.parse(diagnosticBytes);
    if (diagnosticManifest.role!=='raw_diagnostics_only' || diagnosticManifest.composite_score!==null
        || diagnosticManifest.core_promotion!==false || Object.keys(diagnosticManifest.files).sort().join(',')!=='history.json,research.json') throw new Error('Invalid diagnostic role');
    for (const [file,sha] of Object.entries(diagnosticManifest.files)) {
      if (hash(await bytes(`/data/diagnostics/releases/${diagnostic.release_id}/${file}`))!==sha) throw new Error('Diagnostic checksum mismatch');
    }
    if (hash(await bytes('/data/core-v2/latest.json')) !== hash(expectedCoreTenPointer)
        || hash(await bytes('/data/core-v2/status.json')) !== hash(expectedCoreTenStatus)) continue;
    const ten = JSON.parse(expectedCoreTenPointer);
    if (!/^core10-[a-f0-9]{20}$/.test(ten.release_id) || ten.methodology_version!=='core-v0.2.0'
        || ten.manifest_url!==`/data/core-v2/releases/${ten.release_id}/manifest.json`) throw new Error('Invalid Core 10 pointer');
    const tenBytes = await bytes(ten.manifest_url);
    if (hash(tenBytes)!==ten.manifest_sha256) continue;
    const tm=JSON.parse(tenBytes);
    if (tm.required_coverage!==10 || tm.research_only!==true || tm.protocol_sha256!=='43fc1f29c02868f4d1f5b02ed0f121fc15d9e79e5f886dbaf2061e8b8837d404'
        || Object.keys(tm.files).sort().join(',')!=='history.json,research.json') throw new Error('Invalid Core 10 methodology');
    // A failed upstream join deliberately retains the previous valid composite and its pinned parents.
    for (const ref of Object.values(tm.parents)) {
      if (hash(await bytes(ref.manifest_url))!==ref.manifest_sha256) throw new Error('Core 10 parent checksum mismatch');
    }
    for (const [file,sha] of Object.entries(tm.files)) {
      if (hash(await bytes(`/data/core-v2/releases/${ten.release_id}/${file}`))!==sha) throw new Error('Core 10 checksum mismatch');
    }
    verified = true;
    console.log(JSON.stringify({ production_verified: true, release_id: pointer.release_id, proxy_release_id: proxy.release_id, extended_release_id:extended.release_id, diagnostic_release_id:diagnostic.release_id, core_ten_release_id:ten.release_id }));
    break;
  } catch { /* Keep waiting for the complete new deployment, never accept a mixed release. */ }
}
if (!verified) throw new Error('Production verification timed out; retain artifacts and inspect Pages deployment.');
