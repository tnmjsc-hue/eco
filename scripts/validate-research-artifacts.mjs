import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');

async function readJson(path) {
  return JSON.parse(await readFile(resolve(root, path), 'utf8'));
}

const protocol = await readJson('configs/research/core-v0.1.0.json');
const feasibility = await readJson('configs/research/metric-feasibility-v0.1.0.json');
const d05Evidence = await readJson('docs/evidence/d05-live-probe-2026-10-03.json');

assert.equal(protocol.status, 'frozen_for_research_only');
assert.equal(protocol.methodology_version, 'core-v0.1.0');
assert.deepEqual(protocol.components, ['E1', 'E5', 'E6', 'E7']);
assert.equal(protocol.timestamp_policy.include_open_day, false);
assert.equal(protocol.timestamp_policy.source_available_at_required_for_as_published, true);
assert.equal(protocol.raw_features.E1, 'ln(SMA111(PriceUSD) / (2 * SMA350(PriceUSD)))');
assert.equal(protocol.raw_features.E5, 'ln(PriceUSD / SMA730(PriceUSD))');
assert.match(protocol.raw_features.E6, /u_lt_t_min_observations_730/);
assert.match(protocol.raw_features.E7, /rolling_std_population\(CapMrktCurUSD, u_lt_t, min_observations_365\)/);
assert.equal(protocol.raw_features.derived_realized_cap, 'CapMrktCurUSD / CapMVRVCur');
assert.equal(protocol.normalizer.lookback_calendar_days, 1460);
assert.equal(protocol.normalizer.min_raw_observations, 365);
assert.equal(protocol.normalizer.lower_quantile, 0.05);
assert.equal(protocol.normalizer.upper_quantile, 0.95);
assert.equal(protocol.normalizer.quantile_method, 'linear');
assert.equal(protocol.normalizer.clip_min, 0);
assert.equal(protocol.normalizer.clip_max, 100);
assert.deepEqual(protocol.aggregation.price_group, ['E1', 'E5', 'E6']);
assert.deepEqual(protocol.aggregation.valuation_group, ['E7']);
assert.equal(protocol.aggregation.price_group_weight + protocol.aggregation.valuation_group_weight, 1);
assert.equal(protocol.aggregation.require_all_components, true);
assert.equal(protocol.aggregation.missing_score, null);
assert.equal(protocol.evaluation.primary_label.horizon_calendar_days, 365);
assert.equal(protocol.evaluation.primary_label.drawdown_threshold, -0.5);
assert.equal(protocol.evaluation.primary_label.not_a_cycle_top_label, true);
assert.equal(protocol.evaluation.primary_test_start, '2020-01-01');
assert.equal(protocol.evaluation.primary_test_end, 'derive_from_latest_observation_minus_365_days');
assert.equal(protocol.evaluation.primary_metric, 'average_precision');
assert.equal(protocol.evaluation.baselines.length, 3);
assert.equal(protocol.evaluation.bootstrap.method, 'paired_moving_block');
assert.equal(protocol.evaluation.bootstrap.block_calendar_days, 90);
assert.equal(protocol.evaluation.bootstrap.replicates, 10000);
assert.equal(protocol.evaluation.bootstrap.seed, 20261003);
assert.equal(protocol.evaluation.bootstrap.confidence_level, 0.95);
assert.match(protocol.evaluation.success_rule, /vs_each_baseline/);
assert.ok(protocol.limitations.includes('score_0_100_is_not_probability'));
const researchPlan = await readFile(resolve(root, 'docs/MASTER_PLAN.md'), 'utf8');
assert.match(researchPlan, /ADR-001 là nguồn chuẩn duy nhất/);
assert.doesNotMatch(researchPlan, /Giữ 2025-01-01 đến ngày mới nhất có label hoàn tất làm holdout ban đầu/);

assert.equal(feasibility.register_version, 'metric-feasibility-v0.1.0');
assert.equal(feasibility.rights_policy, 'public_derived_and_commercial_rights_unconfirmed');
assert.equal(feasibility.vintage_policy, 'historical_source_availability_and_revision_vintages_unknown');
assert.deepEqual(feasibility.metrics.map(({ id }) => id), ['E1', 'E2', 'E3', 'E4', 'E5', 'E6', 'E7', 'E8', 'E9']);

for (const metric of feasibility.metrics) {
  assert.ok(metric.concept, `${metric.id}: concept required`);
  assert.ok(metric.role, `${metric.id}: role required`);
  assert.ok(metric.provider, `${metric.id}: provider required`);
  assert.ok(metric.metrics.length > 0, `${metric.id}: at least one provider metric required`);
  assert.ok(metric.sources.length > 0, `${metric.id}: source references required`);
  assert.ok(metric.sources.every((source) => source.startsWith('https://')), `${metric.id}: sources must be HTTPS URLs`);
  assert.ok(metric.coverage.status, `${metric.id}: coverage status required`);
  assert.ok(metric.coverage.evidence, `${metric.id}: evidence summary required`);
  assert.ok(metric.rights, `${metric.id}: rights status required`);
  assert.ok(metric.vintage, `${metric.id}: vintage status required`);
  assert.ok(metric.decision, `${metric.id}: decision required`);
}

assert.deepEqual(
  feasibility.metrics.filter(({ role }) => role === 'core_candidate').map(({ id }) => id),
  ['E1', 'E5', 'E6', 'E7'],
);
assert.ok(feasibility.metrics.find(({ id }) => id === 'E2').decision.includes('not_an_independent_vote'));
assert.ok(feasibility.metrics.find(({ id }) => id === 'E4').decision.includes('r_and_d_only'));
assert.ok(feasibility.metrics.find(({ id }) => id === 'E8').decision.includes('do_not_relabel'));
assert.ok(feasibility.metrics.find(({ id }) => id === 'E9').decision.includes('not_selected'));

assert.equal(d05Evidence.audit_id, 'D05');
assert.equal(d05Evidence.audit_version, 'metric-feasibility-v0.1.1');
assert.equal(d05Evidence.authorization, 'no_api_key');
assert.equal(d05Evidence.coinmetrics_catalog.http_status, 200);
assert.equal(d05Evidence.coinmetrics_catalog.one_day_entries.length, 7);
const probeStatuses = Object.fromEntries(d05Evidence.coinmetrics_timeseries.map(({ metric, http_status }) => [metric, http_status]));
assert.deepEqual(probeStatuses, {
  CapRealUSD: 403,
  FeeTotNtv: 200,
  FeeTotUSD: 403,
  FeeBlobTotNtv: 403,
  FeePrioTotNtv: 403,
  SplyAct1yr: 403,
  TxTfrValAdjUSD: 403,
});
const feeProbe = d05Evidence.coinmetrics_timeseries.find(({ metric }) => metric === 'FeeTotNtv');
assert.equal(feeProbe.row_count, 3);
assert.equal(feeProbe.non_null_value_count, 3);
assert.ok(d05Evidence.glassnode_documentation.every(({ http_status }) => http_status === 200));

process.stdout.write('D04 protocol invariants: PASS\nD05 feasibility register E1-E9: PASS\n');
