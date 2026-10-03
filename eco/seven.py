"""Seven-component Experimental releases from verified, immutable parent releases."""
import argparse
from datetime import date, datetime, timezone
import math
from pathlib import Path
import re
import numpy as np
from .pipeline import ROOT, digest, encode, read_json, verify_release
from .research import labels, ap, statistics, spearman, REGIMES, _regime_for
from .proxy_pipeline import ATTRIBUTION

VERSION = "extended-v0.1.0"
PROTOCOL = VERSION + "-protocol-1"
PROTOCOL_HASH = "719b9873e7e96546f829df915051d993dafbb960e53878495c1bce249c948bcb"
CORE_IDS = ("E1", "E5", "E6", "E7")
PROXY_IDS = ("exchange_share", "address_activity", "value_per_transfer")
IDS = CORE_IDS + PROXY_IDS
WEIGHTS = dict(zip(IDS, (.125, .125, .125, .375, 1/12, 1/12, 1/12)))

def protocol():
    config = read_json(ROOT / "configs/research/extended-v0.1.0.json")
    if digest(encode(config)) != PROTOCOL_HASH or config["weights"] != WEIGHTS:
        raise ValueError("frozen Extended protocol changed")
    return config

def aggregate(components, selected=IDS):
    if not selected or len(set(selected)) != len(selected) or any(m not in WEIGHTS for m in selected):
        return None
    values = [components.get(m) for m in selected]
    if any(v is None for v in values): return None
    if any(isinstance(v, bool) or not isinstance(v, (int,float)) or not math.isfinite(v) or not 0 <= v <= 100 for v in values):
        raise ValueError("invalid normalized component")
    return sum(components[m]*WEIGHTS[m] for m in selected)/sum(WEIGHTS[m] for m in selected)

def join(core_rows, proxy_rows):
    def calendar(rows):
        days = [r["date"] for r in rows]
        if not days or days != sorted(set(days)) or any((date.fromisoformat(b)-date.fromisoformat(a)).days != 1 for a,b in zip(days,days[1:])):
            raise ValueError("parent calendar is not continuous")
    calendar(core_rows); calendar(proxy_rows)
    proxies = {r["date"]:r for r in proxy_rows}
    result = []
    for core in core_rows:
        proxy = proxies.get(core["date"])
        components = {m: core["components"][m] for m in CORE_IDS}
        reasons = {m:core["reasons"][m] for m in CORE_IDS}
        flags = {m:[] for m in CORE_IDS}
        for m in PROXY_IDS:
            item = proxy["metrics"][m] if proxy else None
            components[m] = item["score"] if item else None
            reasons[m] = (item["raw_reason"] or item["score_reason"]) if item else "parent_date_unavailable"
            flags[m] = item["source_flags"] if item else []
        for m,v in components.items():
            if (v is not None and (isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not 0 <= v <= 100)
                    or (v is None and not isinstance(reasons[m],str)) or (v is not None and reasons[m] is not None)
                    or not isinstance(flags[m],list) or any(not isinstance(f,str) for f in flags[m])):
                raise ValueError("invalid parent component/reason/flags")
        if core["score"] != aggregate_core(components):
            if core["score"] is None or aggregate_core(components) is None or abs(core["score"]-aggregate_core(components)) > 1e-8:
                raise ValueError("Core parent aggregation mismatch")
        closed = core["period_closed_at_retrieval"]
        result.append({"date":core["date"], "price_usd":core["price_usd"], "core_score":core["score"],
                       "score":aggregate(components) if closed else None,
                       "coverage":sum(v is not None for v in components.values()), "components":components,
                       "reasons":reasons, "source_flags":flags, "period_closed_at_retrieval":closed,
                       "source_row_present":core["source_row_present"] and bool(proxy and proxy["source_row_present"]),
                       "proxy_row_present":bool(proxy and proxy["source_row_present"])})
    return result

def aggregate_core(components):
    if any(components[m] is None for m in CORE_IDS): return None
    return sum(components[m]/6 for m in CORE_IDS[:3]) + components["E7"]/2

def evaluate(rows, replicates=10000):
    future = labels(rows)
    chosen = [r for r in rows if r["date"] >= "2020-01-01" and r["score"] is not None and r["date"] in future]
    if not chosen: raise ValueError("no completed evaluation horizon")
    y = [future[r["date"]] for r in chosen]
    scores = {"extended":[r["score"] for r in chosen], "core":[r["core_score"] for r in chosen],
              "normalized_E7_only":[r["components"]["E7"] for r in chosen],
              "normalized_price_group_only":[sum(r["components"][m] for m in CORE_IDS[:3])/3 for r in chosen]}
    baselines = tuple(n for n in scores if n != "extended")
    # Tie-preserving, weighted AP; sort once, verify against the independent research function.
    ya = np.asarray(y,dtype=float); plans = {}
    for n,v in scores.items():
        a = np.asarray(v); order = np.argsort(-a,kind="stable")
        plans[n] = (order,np.r_[np.flatnonzero(np.diff(a[order]) != 0),len(a)-1])
    def estimates(w):
        positive = float(np.sum(w*ya))
        if positive == 0: return None
        values = {}
        for n,(order,ends) in plans.items():
            tp = np.cumsum(w[order]*ya[order])[ends]; total = np.cumsum(w[order])[ends]
            values[n] = float(np.sum(np.divide(tp,total,out=np.zeros_like(tp),where=total>0)*np.diff(np.r_[0.,tp]))/positive)
        return values
    check = estimates(np.ones(len(y)))
    if check is None or any(abs(check[n]-ap(y,v)) > 1e-12 for n,v in scores.items()):
        raise ValueError("Extended AP cross-check failed")
    offsets = np.asarray([(date.fromisoformat(r["date"])-date.fromisoformat(chosen[0]["date"])).days for r in chosen])
    length = int(offsets[-1]+1); rng = np.random.default_rng(20261003); deltas = {n:[] for n in baselines}
    for _ in range(replicates):
        starts = rng.integers(0,length-90+1,size=math.ceil(length/90))
        sampled = (starts[:,None]+np.arange(90)).ravel()[:length]
        result = estimates(np.bincount(sampled,minlength=length)[offsets])
        if result:
            for n in baselines: deltas[n].append(result["extended"]-result[n])
    comparisons = {}
    for n,v in deltas.items():
        lo,hi = np.quantile(v,[.025,.975],method="linear") if v else (None,None)
        comparisons[n] = {"ap_delta":check["extended"]-check[n],"lower_95":float(lo) if v else None,
                          "upper_95":float(hi) if v else None,"valid_replicates":len(v)}
    components = {m:[r["components"][m] for r in chosen] for m in IDS}
    regimes = {}
    for regime in REGIMES:
        indices = [i for i,r in enumerate(chosen) if _regime_for(r["date"])["id"] == regime["id"]]
        ry = [y[i] for i in indices]
        regimes[regime["id"]] = {"n":len(indices),"positive_labels":sum(ry),
            "models":{n:statistics(ry,[v[i] for i in indices]) for n,v in scores.items()} if indices else {}}
    return {"methodology_version":VERSION,"protocol":PROTOCOL,"status":"exploratory_reconstructed_only",
            "n":len(y),"start":chosen[0]["date"],"end":chosen[-1]["date"],"positive_labels":sum(y),
            "prevalence":sum(y)/len(y),"statistics":{n:statistics(y,v) for n,v in scores.items()},
            "comparisons":comparisons,"bootstrap":{"replicates":replicates,"block_calendar_days":90,"seed":20261003},
            "correlations":{m:{n:spearman(v,components[n]) for n in IDS if n != m} for m,v in components.items()},
            "ablation":{m:statistics(y,[aggregate(r["components"],tuple(n for n in IDS if n != m)) for r in chosen]) for m in IDS},
            "regime_analysis":regimes,"decision":"publish_experimental_preview_no_predictive_validation_claim",
            "limitations":protocol()["limitations"] + ["reused_holdout_is_exploratory"]}

def parent(public, prefix, version, pattern):
    root = public/"data"/prefix
    pointer = read_json(root/"latest.json")
    release_id = pointer.get("release_id","")
    url = f"/data/{prefix+'/' if prefix else ''}releases/{release_id}/manifest.json"
    if not re.fullmatch(pattern,release_id) or pointer.get("manifest_url") != url:
        raise ValueError("parent pointer contract mismatch")
    folder = root/"releases"/release_id
    manifest_bytes = (folder/"manifest.json").read_bytes()
    if digest(manifest_bytes) != pointer["manifest_sha256"]: raise ValueError("parent manifest checksum mismatch")
    manifest = verify_release(folder); history = read_json(folder/"history.json")
    if (manifest.get("methodology_version") != version or manifest.get("series_type") != "reconstructed"
            or history.get("asset") != "eth" or history.get("methodology_version") != version
            or history.get("release_id") != release_id or set(manifest["files"]) != {"history.json","research.json"}):
        raise ValueError("wrong parent ETH/research contract")
    if prefix:
        if (manifest.get("attribution") != ATTRIBUTION or not manifest.get("private_backup",{}).get("all_objects_readback_verified")
                or manifest.get("protocol_sha256") != "4f3b9ebdf2ce0c69704174c47cd5183731942b1051321e33596d80d39f71af2c"):
            raise ValueError("proxy licence/protocol gate failed")
    elif manifest.get("license_url") != "https://creativecommons.org/licenses/by-nc/4.0/" or manifest.get("protocol_sha256") != "da76f0d4357f54fc319d49e57323e95f3bd33338a2b5774a5cda54e228ce7d09":
        raise ValueError("Core licence/protocol gate failed")
    return {"release_id":release_id,"methodology_version":version,"manifest_url":url,
            "manifest_sha256":pointer["manifest_sha256"],"history_sha256":manifest["files"]["history.json"],
            "last_observation_date":manifest["last_observation_date"]}, history["rows"]

def update(public, output, *, replicates=10000):
    config = protocol()
    if replicates != 10000: raise ValueError("public Extended evaluation requires 10000 bootstrap replicates")
    core,core_rows = parent(public,"","core-v0.1.0",r"core-[a-f0-9]{20}")
    proxy,proxy_rows = parent(public,"network-proxies","network-proxies-v0.1.0",r"proxy-[a-f0-9]{20}")
    engine_hash = digest(b"".join((ROOT/p).read_bytes() for p in ("eco/seven.py","eco/research.py")))
    identity = {"methodology_version":VERSION,"protocol_sha256":PROTOCOL_HASH,"engine_sha256":engine_hash,
                "parents":{"core":core,"proxies":proxy},"bootstrap_replicates":replicates}
    release_id = "extended-"+digest(encode(identity))[:20]
    root = public/"data/extended"; pointer_path = root/"latest.json"
    previous = read_json(pointer_path) if pointer_path.exists() else None
    if previous and previous["release_id"] == release_id:
        folder = root/"releases"/release_id
        if digest((folder/"manifest.json").read_bytes()) != previous["manifest_sha256"]: raise ValueError("Extended manifest changed")
        verify_release(folder)
        return "unchanged",release_id
    rows = join(core_rows,proxy_rows); revision = None
    if previous:
        old_folder = root/"releases"/previous["release_id"]
        if digest((old_folder/"manifest.json").read_bytes()) != previous["manifest_sha256"]: raise ValueError("old Extended manifest checksum mismatch")
        verify_release(old_folder); before = {r["date"]:r for r in read_json(old_folder/"history.json")["rows"]}
        if set(before)-{r["date"] for r in rows}: raise ValueError("Extended calendar shrank")
        changed = []
        for i,r in enumerate(rows):
            old = before.get(r["date"])
            if not old: continue
            if any(old["components"][m] is not None and r["components"][m] is None for m in IDS):
                raise ValueError("parent lost previously usable components")
            equivalent = all(old.get(k) == r.get(k) for k in ("reasons","source_flags","coverage","source_row_present","proxy_row_present","period_closed_at_retrieval"))
            for k in ("score","core_score","price_usd",*IDS):
                a,b = (old["components"][k],r["components"][k]) if k in IDS else (old[k],r[k])
                equivalent &= a == b or (a is not None and b is not None and math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-8))
            if equivalent: rows[i] = old
            else: changed.append(r["date"])
        revision = {"previous_release_id":previous["release_id"],"changed_dates":changed,
                    "added_dates":[r["date"] for r in rows if r["date"] not in before],"reason":"parent_or_engine_revision"}
    research = evaluate(rows,replicates)
    valid = [r for r in rows if r["score"] is not None]
    if not valid: raise ValueError("no valid Extended score")
    history = {"schema_version":"1.0.0","release_id":release_id,"methodology_version":VERSION,"asset":"eth",
               "series_type":"reconstructed","weights":WEIGHTS,"attribution":ATTRIBUTION,"rows":rows}
    files = {"history.json":encode(history),"research.json":encode(research)}
    manifest = {"schema_version":"1.0.0","release_id":release_id,**identity,"protocol":PROTOCOL,"asset":"eth",
                "series_type":"reconstructed","research_only":True,"weights":WEIGHTS,"required_coverage":7,
                "rows":len(rows),"score_rows":len(valid),"first_observation_date":rows[0]["date"],
                "last_observation_date":rows[-1]["date"],"first_score_date":valid[0]["date"],
                "last_valid_score_date":valid[-1]["date"],"last_valid_score":valid[-1]["score"],
                "missing_dates":[r["date"] for r in rows if not r["source_row_present"]],"pending_dates":[],
                "source_available_at":None,"computed_at":datetime.now(timezone.utc).isoformat(),
                "attribution":ATTRIBUTION,"license_url":ATTRIBUTION["licence_url"],"limitations":config["limitations"],
                "revision":revision,"files":{n:digest(b) for n,b in files.items()}}
    # Private computed mirror and immutable public derived assets; raw remains in parent snapshots/R2.
    for target in (output/release_id,root/"releases"/release_id):
        if target.exists(): raise ValueError("immutable Extended release already exists")
        target.mkdir(parents=True)
        for n,b in files.items(): (target/n).write_bytes(b)
        (target/"manifest.json").write_bytes(encode(manifest)); verify_release(target)
    pointer = {"release_id":release_id,"methodology_version":VERSION,"manifest_url":f"/data/extended/releases/{release_id}/manifest.json",
               "manifest_sha256":digest(encode(manifest))}
    temporary = root/"latest.tmp"; temporary.write_bytes(encode(pointer)); temporary.replace(pointer_path)
    return "revised" if revision and revision["changed_dates"] else "published",release_id

def daily(public, output):
    root = public/"data/extended"; root.mkdir(parents=True,exist_ok=True)
    try:
        outcome,release_id = update(public,output)
        manifest = read_json(root/"releases"/release_id/"manifest.json")
        if manifest["last_valid_score_date"] < manifest["last_observation_date"]: outcome = "source_pending"
        failure = None
    except Exception:
        old = root/"latest.json"; release_id = read_json(old)["release_id"] if old.exists() else None
        outcome = "failed"; failure = "parent_validation_or_computation"
    (root/"status.json").write_bytes(encode({"methodology_version":VERSION,"release_id":release_id,"outcome":outcome,
        "last_attempt_at":datetime.now(timezone.utc).isoformat(),"schedule_vi":"Sau mỗi batch Core (10:17/14:17) và proxy (10:47/14:47 giờ Việt Nam)",
        "failure_stage":failure}))
    if failure: raise RuntimeError("Extended update failed; previous release preserved") from None
    return {"status":outcome,"release_id":release_id}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--public",type=Path,default=ROOT/"public")
    parser.add_argument("--output",type=Path,default=ROOT/"data/computed/extended")
    args = parser.parse_args(); print(__import__("json").dumps(daily(args.public,args.output)))
