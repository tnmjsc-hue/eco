"""Pure, causal cross-indicator assessment. No clock, provider or filesystem IO."""
from collections import Counter
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import calendar as months
import json
import re

VERSION = "macro-cross-v1.0.1"
SCHEMA = "macro-assessment-v1.0.1"
RULESET_SHA256 = "7a8f1e8fb29a70978588a4ec320ddb0d96437c6a319600592e3cf0622a20f86a"
DIRECTIONS = ("positive", "negative", "flat", "mixed", "unknown")
ASSETS = ("usd", "gold", "crypto_risk_assets")
OMIT_STATE = {"assessment_id", "state_id", "previous_assessment_id", "as_of", "generated_at",
              "batch_status_id", "batch_status_sha256", "context_transition", "change_reason",
              "changed_observations", "changed_observation_ids"}
RULE_IDS = ["X01_EMPLOYMENT_SPLIT", "X02_CONSUMER_SPLIT", "X03_WEEKLY_VS_MONTHLY",
            "X04_PRODUCER_VS_CONSUMER", "X05_INFLATION_ACTIVITY_TENSION",
            "X06_DISINFLATION_NONWEAKENING", "X07_DISINFLATION_WEAK_ACTIVITY",
            "X08_GROWTH_LABOR_SPLIT", "X09_REVISION", "X10_NO_CONSENSUS",
            "X11_DUPLICATE_INFORMATION", "X12_NEGATIVE_ACTIVITY_LEVEL"]


def canonical(value, field=""):
    if isinstance(value, float):
        raise ValueError("Decimal fields must be text")
    if isinstance(value, dict):
        return {k: canonical(v, k) for k, v in sorted(value.items())}
    if isinstance(value, list):
        items = [canonical(v) for v in value]
        if field.endswith("_ids") or field in {"quality_flags", "warnings", "mechanism_codes", "unobserved_conditions", "reason_ids"}:
            return sorted(set(items))
        keys = {"observations": ("metric_id","reference_period","usable_at","observation_id"),
                "numeric_evidence": ("metric_id",), "signals": ("metric_id", "observation_id"), "triggered_rules": ("rule_id",),
                "changed_observations": ("metric_id",), "excluded_inputs": ("observation_id", "reason"),
                "per_metric_relations": ("metric_id", "observation_id")}
        if field in keys:
            return sorted(items, key=lambda r: tuple(str(r.get(k, "")) for k in keys[field]))
        return items
    return value


def encode(value):
    return json.dumps(canonical(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return sha256(encode(value)).hexdigest()


def utc(value):
    if not isinstance(value, str):
        raise ValueError("missing UTC timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() != timedelta(0):
        raise ValueError("timestamp must be aware UTC")
    return parsed


def decimal(value):
    if not isinstance(value, str) or not re.fullmatch(r"-?\d+(?:\.\d+)?", value):
        raise ValueError("invalid decimal text")
    try:
        result = Decimal(value)
    except InvalidOperation:
        raise ValueError("invalid decimal") from None
    if not result.is_finite():
        raise ValueError("nonfinite decimal")
    return result


def decimal_text(value):
    value = decimal(value) if isinstance(value, str) else value
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ValueError("invalid decimal")
    return "0" if value == 0 else format(value, "f").rstrip("0").rstrip(".") if "." in format(value, "f") else format(value, "f")


def prior_period(period):
    if re.fullmatch(r"\d{4}-\d{2}", period):
        y, m = map(int, period.split("-")); date(y, m, 1)
        return f"{y-(m==1):04d}-{12 if m==1 else m-1:02d}"
    if re.fullmatch(r"\d{4}-Q[1-4]", period):
        y, q = int(period[:4]), int(period[-1])
        return f"{y-(q==1):04d}-Q{4 if q==1 else q-1}"
    return (date.fromisoformat(period) - timedelta(days=7)).isoformat()


def period_end(period):
    if re.fullmatch(r"\d{4}-\d{2}", period):
        y, m = map(int, period.split("-"))
        return date(y, m, months.monthrange(y, m)[1])
    if re.fullmatch(r"\d{4}-Q[1-4]", period):
        y, m = int(period[:4]), int(period[-1])*3
        return date(y, m, months.monthrange(y, m)[1])
    return date.fromisoformat(period)


def reduce_directions(items):
    values = set(items)
    if not values <= set(DIRECTIONS):
        raise ValueError("invalid direction enum")
    if "mixed" in values or {"positive", "negative"} <= values:
        return "mixed"
    return next((v for v in DIRECTIONS[:3] if v in values), "unknown")


def direction(actual, previous, orientation, epsilon):
    delta = decimal(actual) - decimal(previous)
    signed = delta * Decimal(orientation)
    bound = decimal(epsilon)
    return delta, signed, "positive" if signed >= bound else "negative" if signed <= -bound else "flat"


def pipeline_state(status, as_of):
    cutoff = utc(as_of)
    try:
        known, check = utc(status.get("known_at")), utc(status.get("last_successful_source_check_at"))
    except (AttributeError, ValueError, TypeError):
        return "unknown", "pipeline_status_unknown"
    if known > cutoff or check > cutoff:
        return "unknown", "future_pipeline_status"
    if check > known:
        return "unknown", "invalid_pipeline_chronology"
    return ("stale", "source_check_expired") if cutoff-check > timedelta(hours=48) else ("fresh", None)


def route(i, l, g, ruleset, pipeline="fresh", negative_level=False):
    if any(v not in DIRECTIONS for v in (i,l,g)) or pipeline not in {"fresh","stale","unknown"}:
        raise ValueError("invalid enum")
    a = reduce_directions([l,g])
    if pipeline != "fresh":
        regime = "R_STALE"
    elif sum(v != "unknown" for v in (i,l,g)) < 2:
        regime = "R_INSUFFICIENT"
    elif "mixed" in (i,a):
        regime = "R_CONFLICT"
    elif i == "unknown":
        regime = "R_ACTIVITY_ONLY"
    else:
        regime = ruleset["matrix"][i][a]
    assets = list(ruleset["regime_assets"][regime])
    if negative_level and assets[2] == "supportive":
        assets[2] = "mixed"
    return regime, tuple(assets)


def validate_observation(o, registry, calendar):
    r = registry.get(o.get("metric_id"))
    if not r:
        return "unsupported_metric"
    for field in ("provider", "series_id", "unit", "transform", "seasonal_adjustment"):
        if o.get(field) != r[field]:
            return "invalid_"+field
    if o.get("previous_semantics") != "prior_period_same_measure":
        return "same_period_revision_not_growth" if o.get("previous_semantics") == "same_period_estimate" else "missing_previous_semantics"
    try:
        p = o["reference_period"]
        if o["previous_period"] != prior_period(p) or date.fromisoformat(o["period_end"]) != period_end(p):
            return "invalid_period_semantics"
        decimal(o["actual"]); decimal(o["previous"])
        usable = utc(o["usable_at"])
        utc(o["source_retrieved_at"]); utc(o["scheduled_at"])
        published = utc(o["source_published_at"]) if o.get("source_published_at") else None
        if o.get("knowledge_basis") == "legacy_snapshot_generated_at":
            if o.get("first_seen_at") is not None or usable != utc(calendar["generated_at"]):
                return "invalid_knowledge_basis"
        elif o.get("knowledge_basis") == "first_seen_ledger":
            first = utc(o["first_seen_at"])
            if usable != max(first, published or first):
                return "invalid_knowledge_basis"
        else:
            return "invalid_knowledge_basis"
    except (ValueError, TypeError, KeyError):
        return "missing_or_invalid_value"
    if o.get("data_status") not in {"official_release", "current_vintage_period_match"}:
        return "unverified_data_status"
    if o.get("calendar_release_id") != calendar["release_id"]:
        return "calendar_parent_mismatch"
    if not any(s["sha256"] == o.get("source_sha256") and s["source_url"] == o.get("source_url") for s in calendar["sources"].values()):
        return "source_hash_not_in_parent"
    if not re.fullmatch(r"obs-[a-f0-9]{20}", o.get("observation_id", "")):
        return "invalid_observation_id"
    return None


def select_observations(observations, calendar, as_of, registry):
    cutoff = utc(as_of)
    visible, excluded, duplicates = [], [], False
    seen = {}
    signatures = set()
    for raw in observations:
        o = deepcopy(raw)
        oid = o.get("observation_id", "")
        try:
            if utc(o["usable_at"]) > cutoff or utc(o["scheduled_at"]) > cutoff or period_end(o["reference_period"]) > cutoff.date():
                continue  # Future input cannot alter exclusions/state at this cutoff.
        except (ValueError, KeyError, TypeError):
            excluded.append({"observation_id":oid,"reason":"invalid_observation_timestamp"}); continue
        if oid in seen:
            if encode(o)!=encode(seen[oid]):raise ValueError("observation ID collision")
            duplicates = True; continue
        seen[oid]=deepcopy(o)
        signature=tuple(o.get(k) for k in ("metric_id","reference_period","usable_at","actual","previous","source_sha256"))
        if signature in signatures:
            duplicates=True;continue
        signatures.add(signature)
        o["excluded_reason"] = validate_observation(o, registry, calendar)
        visible.append(o)
    selected = {}
    for metric in sorted(registry):
        candidates = [o for o in visible if o.get("metric_id") == metric]
        if not candidates:
            continue
        newest_period = max(o["reference_period"] for o in candidates)
        latest = [o for o in candidates if o["reference_period"] == newest_period]
        if len(latest)>1:duplicates=True
        newest = max(utc(o["usable_at"]) for o in latest)
        tied = [o for o in latest if utc(o["usable_at"]) == newest]
        values = {(o.get("actual"),o.get("previous")) for o in tied}
        referenced={o.get("revision_of") for o in tied}
        children = [o for o in tied if o.get("revision_of") in {c["observation_id"] for c in tied} and o["observation_id"] not in referenced]
        chosen = children[0] if len(children)==1 else min(tied,key=lambda o:o["observation_id"])
        if len(values)>1 and len(children)!=1:
            chosen["excluded_reason"] = "ambiguous_vintage"
        selected[metric] = chosen
        for o in candidates:
            if o["observation_id"] != chosen["observation_id"]:
                excluded.append({"observation_id":o["observation_id"],"reason":"superseded_period_or_vintage"})
        age = (cutoff.date()-period_end(chosen["reference_period"])).days
        if age > registry[metric]["max_age_days"]:
            chosen["excluded_reason"] = "stale_observation"
    for o in visible:
        if o.get("metric_id") not in registry:
            excluded.append({"observation_id":o["observation_id"],"reason":"unsupported_metric"})
    return selected, excluded, duplicates, visible


def signals_from(selected, registry):
    signals = {}
    for metric, r in registry.items():
        o = selected.get(metric)
        s = {"metric_id":metric,"observation_id":o["observation_id"] if o else None,
             "event_id":o.get("event_id") if o else None,
             "reference_period":o.get("reference_period") if o else None,
             "previous_period":o.get("previous_period") if o else None,
             "actual":o.get("actual") if o else None,"previous":o.get("previous") if o else None,
             "delta":None,"signed_delta":None,"epsilon":r["epsilon"],"unit":r["unit"],
             "direction":"unknown","level_context":None,"excluded_reason":o.get("excluded_reason") if o else "missing_metric",
             "quality_flags":list(o.get("quality_flags",[])) if o else [],
             "source_url":o.get("source_url") if o else None,"source_sha256":o.get("source_sha256") if o else None}
        if o and not s["excluded_reason"]:
            actual = decimal(o["actual"])
            delta = actual-decimal(o["previous"])
            s["actual"],s["previous"],s["delta"] = map(decimal_text,(actual,decimal(o["previous"]),delta))
            if r["orientation"] is not None:
                _, signed, d = direction(o["actual"],o["previous"],r["orientation"],r["epsilon"])
                s.update(signed_delta=decimal_text(signed),direction=d)
            if metric in {"nfp_change_k_sa","real_gdp_qoq_saar"}:
                s["level_context"] = "negative" if actual<0 else "zero" if actual==0 else "jobs_still_added_but_slower" if metric.startswith("nfp") and delta<0 else "positive_growth_decelerating" if delta<0 else "positive"
            elif r["group"] == "inflation" and actual>0 and delta<0:
                s["level_context"] = "prices_still_rising_more_slowly"
        signals[metric] = s
    return signals


def opposite(a,b):
    return {a,b} == {"positive","negative"}


def axis(children, expected=None, flags=()):
    values=[c["direction"] for c in children]; d=reduce_directions(values)
    available=sum(v!="unknown" for v in values)
    expected=len(children) if expected is None else expected
    return {"direction":d,"available_slots":available,
            "expected_slots":expected,
            "same_direction_slots":values.count(d) if d in DIRECTIONS[:3] else 0,
            "direction_counts":{v:values.count(v) for v in DIRECTIONS},
            "input_observation_ids":[i for c in children for i in c.get("input_observation_ids",[c.get("observation_id")]) if i and c["direction"]!="unknown"],
            "excluded_observation_ids":[i for c in children for i in c.get("excluded_observation_ids",[c.get("observation_id")]) if i and c["direction"]=="unknown"],
            "quality_flags":sorted(set(flags)|({"partial"} if 0<available<expected else set())|{f for c in children for f in c.get("quality_flags",[])})}


def build_axes(signals):
    s=deepcopy(signals); flags=set()
    def align(keys, max_gap, reason):
        usable=[s[k] for k in keys if s[k]["direction"]!="unknown"]
        if len(usable)<2: return
        number=lambda p:int(p[:4])*12+int(p[5:7])
        latest=max(number(v["reference_period"]) for v in usable)
        for v in usable:
            gap=latest-number(v["reference_period"])
            if gap>max_gap:
                v.update(direction="unknown",excluded_reason=reason); v["quality_flags"].append(reason);flags.add(reason)
            elif gap:
                v["quality_flags"].append("period_misaligned");flags.add("period_misaligned")
    align(["nfp_change_k_sa","unemployment_rate_sa"],0,"employment_period_mismatch")
    align(["nfp_change_k_sa","unemployment_rate_sa","jolts_openings_k_sa"],1,"period_gap_excluded")
    pce_keys=["pce_core_mom_sa","pce_headline_mom_sa"]
    align(["cpi_headline_mom_sa",*pce_keys],1,"period_gap_excluded")
    core,headline=s[pce_keys[0]],s[pce_keys[1]]
    pce=axis([core if core["direction"]!="unknown" else headline],expected=1)
    if opposite(core["direction"],headline["direction"]):
        pce=axis([core,headline],expected=1);pce["quality_flags"].append("core_headline_divergence")
    inflation=axis([s["cpi_headline_mom_sa"],pce])
    employment=axis([s["nfp_change_k_sa"],s["unemployment_rate_sa"]])
    if employment["available_slots"]<2: employment["quality_flags"].append("partial_employment_report")
    labor=axis([employment,s["jolts_openings_k_sa"]]);labor["employment"]=employment
    growth=axis([s["real_gdp_qoq_saar"]])
    activity=axis([labor,growth],flags=["mixed_frequency_context"] if growth["available_slots"] else [])
    for supporting, group, prefix in [("initial_claims_k_sa",labor,"weekly_labor"),("ppi_final_demand_mom_sa",inflation,"producer_consumer")]:
        d=s[supporting]["direction"]; target=group["direction"]
        flag="weekly_move_below_threshold" if prefix=="weekly_labor" and d=="flat" else prefix+"_divergence" if opposite(d,target) else prefix+"_aligned" if d==target and d in DIRECTIONS[:2] else "weekly_only_context" if prefix=="weekly_labor" and target=="unknown" else None
        if flag: group["quality_flags"].append(flag); flags.add(flag)
    return s,{"inflation":inflation,"labor":labor,"growth":growth,"activity":activity},flags


def mechanisms(regime, axes, ruleset):
    mapping=ruleset["mechanisms"]
    if regime in {"R_STALE","R_INSUFFICIENT"}:return []
    if regime not in {"R_CONFLICT","R_ACTIVITY_ONLY"}: return sorted(mapping[regime])
    codes={"CHANNEL_DOMINANCE_UNRESOLVED"}
    for name in ("inflation","labor","growth"):
        d=axes[name]["direction"]
        dirs=DIRECTIONS[:2] if d=="mixed" else [d]
        for v in dirs:
            if v not in DIRECTIONS[:2]:continue
            r="R01" if name=="inflation" and v=="positive" else "R04" if name=="inflation" else "R07" if v=="positive" else "R09"
            codes.update(c for c in mapping[r] if name!="inflation" or c!="DEMAND_SUPPORT")
    return sorted(codes)


def state_identity(assessment):
    return {k:v for k,v in assessment.items() if k not in OMIT_STATE}


def assess(bundle, calendar, batch_status, as_of, previous_assessment, ruleset):
    """All arguments are verified objects supplied by caller; input hashes rechecked."""
    cutoff=utc(as_of)
    if bundle.get("schema_version")!="macro-observations-v1.0.0" or not isinstance(bundle.get("observations"),list) or not isinstance(bundle.get("parser_version"),str):
        raise ValueError("invalid observation bundle schema")
    if calendar.get("schema_version")!="1.1.0" or calendar.get("calendar_version")!="us-macro-calendar-v1.1.0" or calendar.get("scope")!="US_major_macro" or not isinstance(calendar.get("events"),list) or not isinstance(calendar.get("sources"),dict):
        raise ValueError("invalid calendar schema")
    if ruleset.get("ruleset_version")!=VERSION or ruleset.get("schema_version")!=SCHEMA:
        raise ValueError("unsupported ruleset")
    rules_hash=digest(ruleset)
    if rules_hash != RULESET_SHA256:
        raise ValueError("frozen ruleset hash mismatch")
    if bundle.get("ruleset_sha256")!=rules_hash or bundle.get("calendar_release_id")!=calendar.get("release_id"):
        raise ValueError("input parent or ruleset mismatch")
    # Calendar serialization is pinned by its existing publisher (compact JSON + LF).
    calendar_hash=sha256((json.dumps(calendar,sort_keys=True,ensure_ascii=False,separators=(",",":"),allow_nan=False)+"\n").encode()).hexdigest()
    if calendar_hash!=bundle.get("calendar_sha256") or calendar.get("private_backup",{}).get("verified") is not True:
        raise ValueError("calendar hash or backup gate failed")
    if batch_status is not None and (not isinstance(batch_status.get("data"),dict) or not isinstance(batch_status.get("id"),str) or not batch_status["id"] or batch_status.get("sha256")!=digest(batch_status["data"])):
        raise ValueError("batch status schema or hash mismatch")
    previous=previous_assessment
    if previous:
        if previous["ruleset_sha256"]!=rules_hash or previous["history_mode"]!="latest_vintage_context" or utc(previous["as_of"])>cutoff:
            raise ValueError("incompatible or future predecessor")
    registry=ruleset["registry"]
    selected, excluded, duplicates, visible=select_observations(bundle["observations"],calendar,as_of,registry)
    for o in selected.values():
        family="jobs" if o.get("release_family_id")=="employment_report" else o.get("release_family_id")
        if any(e.get("kind")==family and e.get("actual") is None and utc(o["scheduled_at"])<utc(e["scheduled_at"])<=cutoff for e in calendar["events"]):
            o["quality_flags"]=sorted(set(o.get("quality_flags",[]))|{"newer_scheduled_result_pending"})
    signals,axes,flags=build_axes(signals_from(selected,registry))
    pipeline, pipeline_reason=pipeline_state(batch_status["data"] if batch_status else None,as_of)
    i,l,g=[axes[n]["direction"] for n in ("inflation","labor","growth")];a=axes["activity"]["direction"]
    negative=any(signals[k]["level_context"]=="negative" and not signals[k]["excluded_reason"] for k in ("nfp_change_k_sa","real_gdp_qoq_saar"))
    regime,labels=route(i,l,g,ruleset,pipeline,negative)
    state="stale_context" if regime=="R_STALE" else "insufficient_context" if regime=="R_INSUFFICIENT" else "assessed"
    all_flags=flags|{f for s in signals.values() for f in s["quality_flags"]}|{f for x in axes.values() for f in x["quality_flags"]}
    full=all(axes[n]["available_slots"]==axes[n]["expected_slots"] for n in ("inflation","labor","growth")) and axes["labor"]["employment"]["available_slots"]==2
    grade="stale" if state=="stale_context" else "insufficient" if state=="insufficient_context" else "conflicted" if "mixed" in (i,l,g,a) else "coherent" if full and not any(f in all_flags for f in ("current_vintage","period_misaligned","employment_period_mismatch","period_gap_excluded","weekly_labor_divergence","producer_consumer_divergence")) else "partial"
    codes=mechanisms(regime,axes,ruleset)
    assets={}
    for asset,label in zip(ASSETS,labels):
        prefixes=ruleset["asset_prefixes"][asset]
        assets[asset]={"conclusion":label,"conditional":True,
                       "mechanism_codes":[c for c in codes if any(c.startswith(p) for p in prefixes) or c in {"GROWTH_RISK","NO_MATERIAL_CHANGE","CHANNEL_DOMINANCE_UNRESOLVED"}],
                       "unobserved_conditions":ruleset["unobserved_conditions"][asset],
                       "reason_ids":[],"template_id":regime+"_"+asset}
    triggered=[]
    def trigger(index, obs=()):
        triggered.append({"rule_id":RULE_IDS[index-1],"observation_ids":[s["observation_id"] for s in obs if s.get("observation_id")],
                          "numeric_evidence":[{k:s.get(k) for k in ("metric_id","actual","previous","delta","signed_delta","reference_period")} for s in obs],"template_id":RULE_IDS[index-1]})
    if opposite(signals["nfp_change_k_sa"]["direction"],signals["unemployment_rate_sa"]["direction"]):trigger(1,[signals["nfp_change_k_sa"],signals["unemployment_rate_sa"]])
    if i=="mixed":trigger(2,[signals[k] for k in ("cpi_headline_mom_sa","pce_core_mom_sa","pce_headline_mom_sa")])
    if "weekly_labor_divergence" in flags:trigger(3,[signals["initial_claims_k_sa"]])
    if "producer_consumer_divergence" in flags:trigger(4,[signals["ppi_final_demand_mom_sa"]])
    context_signals=[s for s in signals.values() if s["direction"]!="unknown" and registry[s["metric_id"]]["group"] in {"inflation","labor","growth"}]
    if i=="positive" and a=="negative":trigger(5,context_signals)
    if i=="negative" and a in {"flat","positive"}:trigger(6,context_signals)
    if i=="negative" and a=="negative":trigger(7,context_signals)
    if opposite(l,g):trigger(8,context_signals)
    if any(o.get("revision_of") for o in selected.values()):trigger(9,[signals[k] for k,o in selected.items() if o.get("revision_of")])
    trigger(10)
    if duplicates:trigger(11)
    if negative:trigger(12,[signals[k] for k in ("nfp_change_k_sa","real_gdp_qoq_saar") if signals[k]["level_context"]=="negative"])
    if negative and route(i,l,g,ruleset,pipeline,False)[1][2]=="supportive":assets["crypto_risk_assets"]["reason_ids"].append(RULE_IDS[-1])
    # Latest verified numeric events remain visible even if their metric is unsupported.
    events=[]
    for e in calendar["events"]:
        if e.get("actual") is None or e.get("data_status") not in {"official_release","current_vintage_period_match"} or utc(e["scheduled_at"])>cutoff:continue
        candidates=[o for o in visible if o.get("event_id")==e["id"]]
        if not candidates and any(o.get("event_id")==e["id"] for o in bundle["observations"]):continue
        known=max((utc(o["usable_at"]) for o in candidates),default=utc(calendar["generated_at"]))
        if known<=cutoff:events.append((e,known))
    latest=None
    if events:
        time=max(e["scheduled_at"] for e,_ in events);batch=[(e,k) for e,k in events if e["scheduled_at"]==time]
        ids=sorted(e["id"] for e,_ in batch)
        peer_signals={k:dict(s,direction="unknown",observation_id=None) if s["event_id"] in ids else deepcopy(s) for k,s in signals.items()}
        _,peer_axes,_=build_axes(peer_signals)
        relations=[]
        for s in signals.values():
            if s["event_id"] not in ids:continue
            group=registry[s["metric_id"]]["group"]
            peer=peer_axes.get(group,{"direction":"unknown"})["direction"]
            d=s["direction"]
            relation="small_change" if d=="flat" else "not_assessable" if d=="unknown" or peer=="unknown" else "mixed_peers" if peer=="mixed" else "aligned" if d==peer else "divergent" if opposite(d,peer) else "not_assessable"
            relations.append({"metric_id":s["metric_id"],"observation_id":s["observation_id"],"relation":relation,"peer_direction":peer})
        order=["divergent","mixed_peers","aligned","small_change","not_assessable"]
        latest={"event_ids":ids,"scheduled_at":time,"usable_at_max":max(k for _,k in batch).isoformat().replace("+00:00","Z"),
                "signal_ids":[s["observation_id"] for s in signals.values() if s["event_id"] in ids and s["observation_id"]],
                "event_context_relation":min((r["relation"] for r in relations),key=order.index,default="not_assessable"),"per_metric_relations":relations}
    excluded.extend({"observation_id":s["observation_id"],"reason":s["excluded_reason"]} for s in signals.values() if s["observation_id"] and s["excluded_reason"])
    result={"schema_version":SCHEMA,"ruleset_version":VERSION,"ruleset_sha256":rules_hash,
            "calendar_release_id":calendar["release_id"],"calendar_sha256":calendar_hash,"observation_bundle_sha256":digest(bundle),
            "batch_status_id":batch_status.get("id") if batch_status else None,"batch_status_sha256":batch_status.get("sha256") if batch_status else None,
            "pipeline_state":pipeline,"pipeline_reason":pipeline_reason,"as_of":as_of,"generated_at":as_of,
            "history_mode":"latest_vintage_context","comparison_basis":"previous_period","latest_event_batch":latest,"latest_event_reason":None if latest else "no_verified_event",
            "signals":list(signals.values()),"axes":axes,"usable_axis_count":sum(v!="unknown" for v in (i,l,g)),
            "assessment_state":state,"evidence_grade":grade,"regime_id":regime,"assets":assets,
            "surprise":{"status":"unavailable","reason":"no_licensed_consensus"},"policy_observation":{"status":"unavailable"},"market_confirmation":{"status":"not_measured"},
            "triggered_rules":triggered,"excluded_inputs":excluded,"warnings":sorted(all_flags)}
    result=canonical(result)
    result["state_id"]="macro-state-"+digest(state_identity(result))[:20]
    if previous and result["state_id"]==previous["state_id"]:
        if encode(state_identity(result))!=encode(state_identity(previous)):raise ValueError("state ID collision")
        return deepcopy(previous)
    result["previous_assessment_id"]=previous["assessment_id"] if previous else None
    result["assessment_id"]="macro-"+digest({"state_id":result["state_id"],"previous_assessment_id":result["previous_assessment_id"]})[:20]
    old={s["metric_id"]:s for s in previous["signals"] if s["observation_id"]} if previous else {}
    new={k:s for k,s in signals.items() if s["observation_id"]}
    changes=[]
    for k in sorted(set(old)|set(new)):
        before,after=old.get(k),new.get(k)
        if (before or {}).get("observation_id")!=(after or {}).get("observation_id"):
            changes.append({"metric_id":k,"before_observation_id":(before or {}).get("observation_id"),"after_observation_id":(after or {}).get("observation_id"),"trigger_event_id":(after or before)["event_id"]})
    result["changed_observations"]=changes
    result["changed_observation_ids"]=sorted({c[k] for c in changes for k in ("before_observation_id","after_observation_id") if c[k]})
    result["context_transition"]="not_computable" if not previous else "context_only" if not changes else "latest_batch_only" if all(c["trigger_event_id"] in (latest or {}).get("event_ids",[]) for c in changes) else "multiple_inputs_changed"
    reasons=set()
    if previous:
        for c in changes:
            if c["before_observation_id"] and c["after_observation_id"] and old[c["metric_id"]]["reference_period"]==new[c["metric_id"]]["reference_period"]:reasons.add("source_revision")
            else:reasons.add("new_observation")
        if any(s["excluded_reason"]=="stale_observation" and old.get(s["metric_id"],{}).get("excluded_reason")!="stale_observation" for s in signals.values()):reasons.add("freshness_expired")
        if (pipeline,pipeline_reason)!=(previous["pipeline_state"],previous["pipeline_reason"]):reasons.add("pipeline_status_changed")
    result["change_reason"]="initial_assessment" if not previous else "multiple_changes" if len(reasons)>1 else next(iter(reasons)) if reasons else "source_snapshot_changed"
    return canonical(result)
