import { backfill } from './backfill-coinmetrics.mjs';
import { mkdir, writeFile } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';

const snapshot = await backfill();
const result = spawnSync(process.execPath, ['scripts/upload-private-snapshot-r2.mjs', snapshot], {
  encoding: 'utf8', timeout: 600000, stdio: ['ignore', 'pipe', 'pipe'],
});
if (result.status !== 0) throw new Error('Private R2 backup failed; no public data will be released.');
const backup = JSON.parse(result.stdout);
if (backup.status !== 'uploaded_private_snapshot' || !backup.objects.length || backup.objects.some(o => !o.readback_verified)) {
  throw new Error('Private R2 readback was not verified.');
}
await mkdir('data/computed', { recursive: true });
await writeFile('data/computed/daily-fetch.json', JSON.stringify({ snapshot, backup }) + '\n');
console.log(JSON.stringify({ stage: 'backup_verified', objects: backup.file_count }));
