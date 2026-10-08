"""Executable specification checks, not the production macro engine/publisher.

Only routing, causal status and publication identity are modeled here. Inputs to
identity checks are synthetic, prevalidated assessment candidates. Provider,
schema/hash verification, normalization, IO and UI remain implementation TODO.
"""
from copy import deepcopy
from datetime import datetime, timedelta
from hashlib import sha256
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "docs/MACRO_CROSS_INDICATOR_RULES.md"
FIXTURE_PATH = ROOT / "docs/fixtures/macro-cross-v1.0.1.json"
STATES = ("positive", "negative", "flat", "mixed", "unknown")
PUBLICATION_FIELDS = frozenset({
    "assessment_id", "state_id", "previous_assessment_id", "as_of", "generated_at",
    "batch_status_id", "batch_status_sha256", "context_transition", "change_reason",
    "changed_observations", "changed_observation_ids",
})


def read_matrix(text):
    rows = re.findall(
        r"^\| `(R0[1-9])` \| (positive|negative|flat) \| (positive|negative|flat)"
        r" \| [^|]+ \| (\w+) \| (\w+) \| (\w+) \|$", text, re.M)
    if len(rows) != 9 or len({(r[1], r[2]) for r in rows}) != 9:
        raise ValueError("Expected nine unique I/A matrix rows in specification")
    return {(i, a): (regime, (usd, gold, crypto)) for regime, i, a, usd, gold, crypto in rows}


def reduce_directions(items):
    present = set(items)
    if not present <= set(STATES):
        raise ValueError("Unknown direction enum")
    if "mixed" in present or {"positive", "negative"} <= present:
        return "mixed"
    for value in ("positive", "negative", "flat"):
        if value in present:
            return value
    return "unknown"


def route(i, l, g, matrix, pipeline="fresh", negative_level=False):
    if any(v not in STATES for v in (i, l, g)) or pipeline not in ("fresh", "stale", "unknown"):
        raise ValueError("Unknown enum")
    if pipeline != "fresh":
        return "R_STALE", ("insufficient_evidence",) * 3
    if sum(v != "unknown" for v in (i, l, g)) < 2:
        return "R_INSUFFICIENT", ("insufficient_evidence",) * 3
    a = reduce_directions((l, g))
    if "mixed" in (i, a):
        return "R_CONFLICT", ("mixed",) * 3
    if i == "unknown":
        return "R_ACTIVITY_ONLY", ("mixed",) * 3
    regime, assets = matrix[(i, a)]
    if negative_level and assets[2] == "supportive":
        assets = (*assets[:2], "mixed")
    return regime, assets


def utc_timestamp(value):
    if not isinstance(value, str):
        raise ValueError("Missing timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() != timedelta(0):
        raise ValueError("Timestamp must be UTC and timezone-aware")
    return parsed


def pipeline_status(status, as_of):
    cutoff = utc_timestamp(as_of)  # Invalid caller cutoff is an error, not unknown data.
    try:
        known = utc_timestamp(status.get("known_at"))
        checked = utc_timestamp(status.get("last_successful_source_check_at"))
    except (ValueError, TypeError, AttributeError):
        return "unknown", "pipeline_status_unknown"
    if known > cutoff or checked > cutoff:
        return "unknown", "future_pipeline_status"
    if checked > known:
        return "unknown", "invalid_pipeline_chronology"
    if cutoff - checked > timedelta(hours=48):
        return "stale", "source_check_expired"
    return "fresh", None


def select_status_vintage(statuses, as_of):
    """Select already verified snapshots; ambiguous equal-time bodies return unknown."""
    cutoff = utc_timestamp(as_of)
    visible = []
    for status in statuses:
        try:
            known = utc_timestamp(status.get("known_at"))
        except (ValueError, TypeError):
            continue
        if known <= cutoff:
            visible.append((known, status))
    if not visible:
        return None
    newest = max(t for t, _ in visible)
    candidates = [s for t, s in visible if t == newest]
    if len({s["batch_status_sha256"] for s in candidates}) != 1:
        return None
    return min(candidates, key=lambda s: s["batch_status_id"])


def transition_relation(changed_event_ids, latest_event_ids, has_previous):
    if not has_previous:
        return "not_computable"
    changed = set(changed_event_ids)
    if not changed:
        return "context_only"
    return "latest_batch_only" if changed <= set(latest_event_ids) else "multiple_inputs_changed"


def pair_changes(before, after):
    """Pair already selected observations by metric, preserving replacement IDs."""
    changes = []
    for metric in sorted(set(before) | set(after)):
        old, new = before.get(metric), after.get(metric)
        old_id = old["observation_id"] if old else None
        new_id = new["observation_id"] if new else None
        if old_id != new_id:
            changes.append(dict(metric_id=metric, before_observation_id=old_id,
                                after_observation_id=new_id,
                                trigger_event_id=(new if new else old)["event_id"]))
    ids = sorted({c[key] for c in changes for key in ("before_observation_id", "after_observation_id")
                  if c[key] is not None})
    return changes, ids


def canonical(value, field=""):
    """Canonicalize the field types exercised by the specification fixtures."""
    if isinstance(value, float):
        raise ValueError("Decimal values must already be canonical strings")
    if isinstance(value, dict):
        return {k: canonical(v, k) for k, v in sorted(value.items())}
    if isinstance(value, list):
        items = [canonical(v) for v in value]
        if field.endswith("_ids") or field in ("quality_flags", "warnings", "mechanism_codes", "unobserved_conditions"):
            return sorted(set(items))
        keys = {"signals": ("metric_id", "observation_id"), "triggered_rules": ("rule_id",)}
        if field in keys:
            return sorted(items, key=lambda v: tuple(v[k] for k in keys[field]))
        return items
    return value


def digest(value):
    body = json.dumps(canonical(value), sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")
    return sha256(body).hexdigest()


def semantic_state(candidate):
    return canonical({k: v for k, v in candidate.items() if k not in PUBLICATION_FIELDS})


def publication_identity(candidate, previous):
    state_id = "macro-state-" + digest(semantic_state(candidate))[:20]
    if previous is not None:
        for key in ("ruleset_version", "ruleset_sha256", "history_mode"):
            if candidate[key] != previous[key]:
                raise ValueError("Incompatible predecessor")
        if utc_timestamp(previous["as_of"]) > utc_timestamp(candidate["as_of"]):
            raise ValueError("Future predecessor")
        if semantic_state(previous) == semantic_state(candidate):
            return previous["state_id"], previous["assessment_id"], True
    parent_id = previous["assessment_id"] if previous is not None else None
    assessment_id = "macro-" + digest({"state_id": state_id, "previous_assessment_id": parent_id})[:20]
    return state_id, assessment_id, False


def materialize_fixture(candidate, previous, store):
    """In-memory identity/replay model. Does not implement production publication IO."""
    state_id, assessment_id, reuse_current = publication_identity(candidate, previous)
    if reuse_current:
        return deepcopy(previous)
    if assessment_id in store:
        saved = store[assessment_id]
        expected_parent = previous["assessment_id"] if previous else None
        if (semantic_state(saved) != semantic_state(candidate)
                or saved["previous_assessment_id"] != expected_parent
                or utc_timestamp(saved["as_of"]) > utc_timestamp(candidate["as_of"])):
            raise ValueError("Immutable identity collision or future artifact")
        return deepcopy(saved)
    result = deepcopy(candidate)
    result.update(state_id=state_id, assessment_id=assessment_id,
                  previous_assessment_id=previous["assessment_id"] if previous else None)
    store[assessment_id] = deepcopy(result)
    return result
