import { backfill } from './backfill-coinmetrics.mjs';

const start = process.argv[2] ?? '2015-07-30';
const asOf = process.argv[3];

if (!asOf) {
  throw new Error('Usage: node scripts/backfill-fee-coinmetrics.mjs [start-utc-date] [as-of-utc-date]');
}

const directory = await backfill(start, asOf, {
  metrics: ['FeeTotNtv'],
  runPrefix: 'coinmetrics-fee-backfill',
  allowZeroMetrics: ['FeeTotNtv'],
});
console.log(`Fee candidate snapshot: ${directory}`);
