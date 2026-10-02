import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { customScore, dateMinus, displayScore, exportCSV, validateHistory } from '../public/data-model.js';

test('strict custom subset weighting, empty/missing never become 0 or 50', () => {
  const row = { components: { E1: 0, E5: 30, E6: 60, E7: 100 } };
  assert.ok(Math.abs(customScore(row, ['E1', 'E5', 'E6', 'E7']) - 65) < 1e-10);
  assert.equal(customScore(row, ['E1', 'E7']), 75);
  assert.equal(customScore(row, []), null);
  assert.equal(customScore(row, ['E2']), null);
  row.components.E6 = null;
  assert.equal(customScore(row, ['E6', 'E7']), null);
  assert.equal(customScore(row, ['E7']), 100);
  assert.equal(displayScore(null), '—');
  assert.equal(displayScore(41.5), '42');
});
test('UTC calendar arithmetic, leap year', () => {
  assert.equal(dateMinus('2024-03-01', 1), '2024-02-29');
  assert.equal(dateMinus('2026-01-01', 1), '2025-12-31');
});
test('release checksums, schema, output agrees with engine', async () => {
  const pointer = JSON.parse(await readFile('public/data/latest.json'));
  const base = `public/data/releases/${pointer.release_id}/`;
  const manifestBytes = await readFile(base + 'manifest.json');
  assert.equal(createHash('sha256').update(manifestBytes).digest('hex'), pointer.manifest_sha256);
  const manifest = JSON.parse(manifestBytes);
  for (const [name, expected] of Object.entries(manifest.files)) assert.equal(createHash('sha256').update(await readFile(base + name)).digest('hex'), expected);
  const data = validateHistory(JSON.parse(await readFile(base + 'history.json')), pointer.release_id);
  assert.equal(data.rows.at(-1).score, null);
  assert.equal(data.rows.at(-1).date, '2026-10-02');
  const last = data.rows.find(r => r.date === manifest.last_valid_score_date);
  assert.equal(last.score, manifest.last_valid_score);
  assert.equal(displayScore(last.score), '41');
  assert.equal(last.coverage, 4);
  assert.ok(Math.abs(customScore(last, ['E1', 'E5', 'E6', 'E7']) - last.score) < 1e-10);
  const bad = structuredClone(data);
  bad.rows.at(-1).score = 50;
  assert.throws(() => validateHistory(bad, pointer.release_id));
  const csv = exportCSV([last, data.rows.at(-1)], ['E7'], 'custom', manifest);
  assert.ok(csv.includes('CC BY-NC 4.0'));
  assert.ok(csv.includes(last.score.toFixed(4)));
  assert.ok(csv.includes('"2026-10-02","","",""'));
});
