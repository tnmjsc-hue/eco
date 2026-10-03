import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');

async function readJson(path) {
  return JSON.parse(await readFile(resolve(root, path), 'utf8'));
}

async function sha256(path) {
  return createHash('sha256').update(await readFile(resolve(root, path))).digest('hex');
}

const protocol = await readJson('configs/research/core-v0.1.0.json');
const feasibility = await readJson('configs/research/metric-feasibility-v0.1.0.json');
const d05Evidence = await readJson('docs/evidence/d05-live-probe-2026-10-03.json');
const sourceContracts = await readJson('configs/research/source-contracts-v0.1.0.json');
const e4Protocol = await readJson('configs/research/e4-fee-candidate-v0.1.0.json');
const e2Evidence = await readJson('docs/evidence/e2-nupl-diagnostic-2026-10-03.json');
const e4Evidence = await readJson('docs/evidence/e4-fee-backfill-2026-10-03.json');
const e4Evaluation = await readJson('docs/evidence/e4-candidate-evaluation-2026-10-03.json');
const remainingSourceAudit = await readJson('docs/evidence/remaining-source-audit-2026-10-03.json');

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

assert.equal(sourceContracts.schema_version, '1.0.0');
assert.equal(sourceContracts.contract_version, 'source-contracts-v0.1.0');
assert.equal(sourceContracts.task_id, 'X00');
assert.equal(sourceContracts.asset_scope, 'eth');
assert.equal(sourceContracts.frequency_scope, '1d');
assert.equal(sourceContracts.timestamp_policy.retrieved_at_is_source_available_at, false);
assert.equal(sourceContracts.timestamp_policy.source_available_at, 'unknown unless provider evidence supplies it');
assert.ok(sourceContracts.unknown_policy.no_inference.includes('retrieved_at must not be copied into source_available_at'));

const evidenceIds = new Set(sourceContracts.evidence.map(({ id }) => id));
assert.deepEqual(
  sourceContracts.evidence.map(({ id }) => id),
  ['D05-summary', 'D03-core-audit', 'metric-feasibility-report', 'rights-policy', 'research-notes', 'remaining-source-audit'],
);
for (const evidence of sourceContracts.evidence) {
  assert.match(evidence.sha256, /^[0-9a-f]{64}$/, `${evidence.id}: SHA-256 required`);
  assert.equal(await sha256(evidence.path), evidence.sha256, `${evidence.id}: evidence hash mismatch`);
  if (evidence.private_manifest) {
    assert.match(evidence.private_manifest.sha256, /^[0-9a-f]{64}$/, `${evidence.id}: private manifest SHA-256 required`);
    assert.equal(evidence.private_manifest.committed, false, `${evidence.id}: private manifest must remain uncommitted`);
  }
  assert.ok(evidence.urls.length > 0, `${evidence.id}: source URL required`);
  assert.ok(evidence.urls.every((url) => url.startsWith('https://')), `${evidence.id}: source URLs must be HTTPS`);
}

assert.deepEqual(
  sourceContracts.contracts.map(({ id }) => id),
  ['E2', 'E3', 'E4', 'E8', 'E9'],
);
for (const contract of sourceContracts.contracts) {
  assert.ok(sourceContracts.status_vocabulary.includes(contract.status), `${contract.id}: invalid status`);
  assert.ok(contract.provider, `${contract.id}: provider required`);
  assert.ok(contract.source, `${contract.id}: source endpoint contract required`);
  assert.ok(contract.coverage?.status, `${contract.id}: coverage status required`);
  assert.ok(contract.coverage?.gaps?.status, `${contract.id}: gaps status required`);
  assert.ok(contract.timing?.source_available_at?.status, `${contract.id}: source availability status required`);
  assert.ok(contract.timing?.lag?.status, `${contract.id}: lag status required`);
  assert.ok(contract.timing?.vintage?.status, `${contract.id}: vintage status required`);
  assert.ok(contract.timing?.revision?.status, `${contract.id}: revision status required`);
  for (const operation of ['cache', 'chart', 'derived', 'csv']) {
    assert.ok(contract.rights?.[operation]?.status, `${contract.id}: rights.${operation}.status required`);
  }
  assert.ok(JSON.stringify(contract).includes('"unit"'), `${contract.id}: unit contract required`);
  assert.ok(contract.evidence_refs.length > 0, `${contract.id}: evidence references required`);
  assert.ok(contract.evidence_refs.every((id) => evidenceIds.has(id)), `${contract.id}: unknown evidence reference`);
  for (const match of JSON.stringify(contract).matchAll(/"(?:response_)?sha256"\s*:\s*"([0-9a-f]+)"/g)) {
    assert.match(match[1], /^[0-9a-f]{64}$/, `${contract.id}: response hash must be SHA-256`);
  }
}

const contractById = Object.fromEntries(sourceContracts.contracts.map((contract) => [contract.id, contract]));
assert.equal(contractById.E2.derived.formula, '1 - 1 / CapMVRVCur');
assert.equal(contractById.E2.role, 'diagnostic_only');
assert.equal(contractById.E2.derived.dependency, 'Algebraically dependent on MVRV/E7; not an independent confirmation');
assert.equal(contractById.E4.coverage.sample_probe.results.FeeTotNtv.http_status, 200);
assert.equal(contractById.E4.coverage.sample_probe.results.FeeTotUSD.http_status, 403);
assert.equal(contractById.E4.coverage.sample_probe.results.FeeBlobTotNtv.http_status, 403);
assert.equal(contractById.E4.coverage.sample_probe.results.FeePrioTotNtv.http_status, 403);
assert.equal(contractById.E9.coverage.sample_probe.http_status, 403);
assert.equal(contractById.E8.coverage.sample_probe.http_status, 403);
assert.equal(contractById.E3.coverage.sample_probe.data_rows, 'not_requested');
assert.match(contractById.E3.decision, /do_not_implement/);
assert.match(contractById.E8.decision, /do_not_relabel/);
assert.match(contractById.E9.decision, /not_selected/);
assert.equal(contractById.E3.status, 'blocked');
assert.equal(contractById.E8.status, 'blocked');
assert.equal(contractById.E9.status, 'blocked');
assert.ok(contractById.E2.rights.derived.attribution_required);
assert.equal(contractById.E3.rights.chart.action, 'do_not_publish');
assert.equal(contractById.E8.rights.csv.action, 'do_not_export');
assert.equal(contractById.E9.rights.cache.status, 'blocked_until_entitlement_verified');

assert.equal(e4Protocol.methodology_version, 'e4-fee-candidate-v0.1.0');
assert.equal(e4Protocol.research_protocol_version, 'e4-fee-v0.1.0-protocol-1');
assert.equal(e4Protocol.input.metric, 'FeeTotNtv');
assert.equal(e4Protocol.raw_feature.formula, 'ln(SMA30(FeeTotNtv) / SMA365(FeeTotNtv))');
assert.equal(e4Protocol.raw_feature.requires_complete_calendar_windows, true);
assert.equal(e4Protocol.normalizer.window_excludes_current_day, true);
assert.equal(e4Protocol.evaluation.status, 'exploratory_until_new_holdout_or_prospective_vintage');
assert.equal(e4Protocol.rights.public_candidate_release, 'blocked_until_metric_specific_rights_and_methodology_decision');
assert.equal(e2Evidence.formula, '1 - 1 / CapMVRVCur');
assert.equal(e2Evidence.contract.not_an_independent_vote, true);
assert.equal(e2Evidence.contract.not_added_to_core_aggregation, true);
assert.equal(e4Evidence.metric, 'FeeTotNtv');
assert.equal(e4Evidence.snapshot.row_count, 4083);
assert.equal(e4Evidence.snapshot.missing_row_date_count, 0);
assert.equal(e4Evidence.snapshot.canonical_sha256, 'c0cd16263f6ebf33ef2c431a057fc827612bdd67b0312927f308e31b8fbe4f8c');
assert.equal(e4Evidence.quality_policy.zero_values_allowed, true);
assert.equal(e4Evaluation.audit_id, 'E4-04');
assert.equal(e4Evaluation.status, 'exploratory_reconstructed_only');
assert.equal(e4Evaluation.statistics.fee_activity.average_precision, 0.24094623735337878);
assert.equal(e4Evaluation.decision, 'retain_r_and_d_only_do_not_promote_to_core_or_public_metric');
assert.equal(e4Evaluation.not_a_probability, true);
assert.equal(remainingSourceAudit.audit_id, 'E3-01/E8-01/E9-01');
assert.equal(remainingSourceAudit.authorization, 'no_api_key_no_paid_subscription');
assert.equal(remainingSourceAudit.scope.no_btc_substitution, true);
assert.deepEqual(
  remainingSourceAudit.findings.map(({ task, status }) => [task, status]),
  [['E3-01', 'blocked'], ['E8-01', 'blocked'], ['E9-01', 'blocked']],
);
assert.deepEqual(
  remainingSourceAudit.glassnode.no_key_probes.map(({ http_status }) => http_status),
  [401, 401, 401],
);
assert.equal(remainingSourceAudit.coinmetrics.sample_status.SplyAct1yr.http_status, 403);
assert.equal(remainingSourceAudit.coinmetrics.sample_status.TxTfrValAdjUSD.http_status, 403);

process.stdout.write('D04 protocol invariants: PASS\nD05 feasibility register E1-E9: PASS\n');
process.stdout.write('X00 source contracts E2/E3/E4/E8/E9: PASS\n');
process.stdout.write('E2 diagnostic contract and E4 candidate protocol: PASS\n');
