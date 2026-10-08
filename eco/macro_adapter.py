"""Normalize only pinned official calendar sources; raw bodies stay private."""
import base64
from copy import deepcopy
from datetime import datetime
from decimal import Decimal
from hashlib import sha256
import re

from . import calendar as cal
from . import macro_assessment as engine

PARSER_VERSION = "official-macro-observations-v1.0.1"
PIO_DEFINITION_URL = "https://www.bea.gov/news/pio-release-additional-information"
BLS_METRICS = {"cpi":"cpi_headline_mom_sa", "payrolls":"nfp_change_k_sa",
               "unemployment":"unemployment_rate_sa", "ppi":"ppi_final_demand_mom_sa",
               "jolts":"jolts_openings_k_sa"}


def legacy_decimal(value):
    if value is None: return None
    if isinstance(value,bool) or not isinstance(value,(int,float,str,Decimal)):
        raise ValueError("invalid numeric source")
    return engine.decimal_text(Decimal(str(value)))


def raw_body(source, expected):
    if not source or source.get("sha256") != expected["sha256"] or source.get("source_url")!=expected["source_url"]:
        raise ValueError("missing pinned source body")
    body = base64.b64decode(source["body"],validate=True) if source.get("body_encoding")=="base64" else source["body"].encode()
    if sha256(body).hexdigest()!=expected["sha256"]:
        raise RuntimeError("source body checksum mismatch")
    return body


def normalize(calendar, calendar_sha256, sources, ruleset, now, prior_bundle=None):
    """Legacy initial snapshot is available only from generated_at; new vintages use ledger time."""
    registry=ruleset["registry"]; observations=[]; rejected=[]
    previous={o["observation_id"]:o for o in (prior_bundle or {}).get("observations",[])}
    prior_periods={(o["metric_id"],o["reference_period"],o["event_id"]):o for o in previous.values()}
    def add(e, metric, actual, prior, source_key, period=None, proof=True, semantics="prior_period_same_measure", flags=()):
        r=registry[metric]; p=period or e["reference_period"]
        expected=calendar["sources"][source_key]
        a,b=legacy_decimal(actual),legacy_decimal(prior)
        identity={"metric_id":metric,"reference_period":p,"actual":a,"previous":b,
                  "source_sha256":expected["sha256"],"parser_version":PARSER_VERSION}
        oid="obs-"+engine.digest(identity)[:20]
        old=previous.get(oid)
        prior_observation=prior_periods.get((metric,p,e["id"]))
        # Parser patch migration with identical pinned values keeps the time
        # those values were already known. It does not assert numeric revision.
        if not old and prior_observation and all(prior_observation.get(k)==v for k,v in (("actual",a),("previous",b),("source_sha256",expected["sha256"]))):old=prior_observation
        same_parent=old and old["calendar_release_id"]==calendar["release_id"]
        first = old.get("first_seen_at") if same_parent else (old.get("first_seen_at") or old["usable_at"]) if old else now if prior_bundle else None
        usable=old["usable_at"] if same_parent else first or calendar["generated_at"]
        value_revision=prior_observation and (prior_observation["actual"],prior_observation["previous"])!=(a,b)
        observations.append({"observation_id":oid,"event_id":e["id"],
          "release_family_id":"employment_report" if metric in {"nfp_change_k_sa","unemployment_rate_sa"} else e["kind"],
          "metric_id":metric,"provider":r["provider"],"series_id":r["series_id"],"actual":a,"previous":b,
          "unit":r["unit"],"transform":r["transform"],"seasonal_adjustment":"SA" if proof else None,
          "reference_period":p,"previous_period":engine.prior_period(p),"previous_semantics":semantics if proof else None,
          "period_end":engine.period_end(p).isoformat(),"scheduled_at":e["scheduled_at"],
          "source_published_at":None,"source_retrieved_at":expected["retrieved_at"],"first_seen_at":first,"usable_at":usable,
          "knowledge_basis":"first_seen_ledger" if first else "legacy_snapshot_generated_at",
          "data_status":e["data_status"],"source_url":expected["source_url"],"source_sha256":expected["sha256"],
          "calendar_release_id":calendar["release_id"],"revision_of":old.get("revision_of") if old and old.get("parser_version")==PARSER_VERSION else prior_observation["observation_id"] if value_revision else None,
          "quality_flags":sorted(set(flags)|({"missing_semantics"} if not proof or semantics is None else set())),"parser_version":PARSER_VERSION,
          "definition_source_url":PIO_DEFINITION_URL if metric.startswith("pce_") else None})
    bls=None
    try:
        bls={r["id"]:r for r in cal.parse_indicators(raw_body(sources.get("bls_data"),calendar["sources"]["bls_data"]))}
    except ValueError:
        rejected.append({"source_key":"bls_data","reason":"missing_or_invalid_pinned_source"})
    for e in calendar["events"]:
        if e.get("actual") is None or not e.get("reference_period"):continue
        if e["provider"]=="bls" and e["kind"] in {"cpi","jobs","ppi","jolts"}:
            keys=["payrolls","unemployment"] if e["kind"]=="jobs" else [e["kind"]]
            for key in keys:
                row=next((r for r in calendar["indicators"] if r["id"]==key),None)
                if not row or row["reference_period"]!=e["reference_period"]:continue
                verified=bls is not None and bls.get(key)==row and row.get("seasonally_adjusted") is True
                add(e,BLS_METRICS[key],row["value"],row["previous"],"bls_data",proof=verified,
                    flags=["current_vintage"]+(["preliminary"] if row.get("preliminary") else []))
        elif e["provider"]=="bea" and e["kind"] in {"pce","gdp","trade"}:
            key="bea_report_"+re.sub(r"[^a-zA-Z0-9_]","_",e["id"])
            if key not in calendar["sources"]:continue
            report=""; verified=False
            try:
                body=raw_body(sources.get(key),calendar["sources"][key]); report=cal.plain(body.decode("utf-8-sig"))
                check=deepcopy(e);check["details"]=[];cal.parse_bea_report(check,body,calendar["sources"][key]["retrieved_at"])
                matched=(check.get("actual"),check.get("previous"),check.get("reference_period"))==(e["actual"],e["previous"],e["reference_period"])
                # PIO's featured monthly price measures follow BEA's published
                # statistical conventions. Require the exact two-month table;
                # a generic PCE mention or a year-over-year table is insufficient.
                month_names=cal.month_names.month_name
                p=e["reference_period"]; previous_p=engine.prior_period(p)
                monthly_table=re.search(r'Personal Income and Related Measures\s*\[Percent change from preceding month\]\s*'+month_names[int(previous_p[5:7])]+r'\s+'+month_names[int(p[5:7])],report,re.I) if e["kind"]=="pce" else None
                verified=matched and (bool(monthly_table) if e["kind"]=="pce" else bool(re.search(r"seasonally adjusted",report,re.I)))
            except ValueError:
                rejected.append({"source_key":key,"reason":"missing_or_invalid_pinned_source"})
            if e["kind"]=="pce":
                add(e,"pce_headline_mom_sa",e["actual"],e["previous"],key,proof=verified)
                # Reparse source to assign a metric; no translated labels or details index used.
                table=re.search(r'PCE price index\s+(-?[\d.]+)\s+(-?[\d.]+)\s+PCE price index excluding food and energy\s+(-?[\d.]+)\s+(-?[\d.]+)',report)
                if table:add(e,"pce_core_mom_sa",table[4],table[3],key,proof=verified)
            elif e["kind"]=="trade":add(e,"trade_balance_bn_sa",e["actual"],e["previous"],key,proof=verified)
            else:
                current=int(e["reference_period"][-1]); names={"first":1,"second":2,"third":3,"fourth":4}
                prior=re.search(r'In the (first|second|third|fourth) quarter(?: of (\d{4}))?, real GDP (?:increased|decreased) ([\d.]+) percent',report,re.I)
                expected=engine.prior_period(e["reference_period"])
                prior_year=int(prior[2]) if prior and prior[2] else int(e["reference_period"][:4])-(current==1)
                prior_matches=prior and f'{prior_year}-Q{names[prior[1].lower()]}'==expected and legacy_decimal(prior[3])==legacy_decimal(abs(e["previous"]))
                # Seasonal metadata can be proven while the comparison period
                # remains unproven. Do not invent a same-quarter estimate.
                add(e,"real_gdp_qoq_saar",e["actual"],e["previous"],key,proof=verified,
                    semantics="prior_period_same_measure" if prior_matches else None)
        elif e["provider"]=="dol" and e["kind"]=="claims":
            local=engine.utc(e["scheduled_at"]).astimezone(cal.ZoneInfo("America/New_York")).date()
            key="dol_report_"+local.strftime("%Y%m%d")
            if key not in calendar["sources"]:continue
            verified=False
            try:
                body=raw_body(sources.get(key),calendar["sources"][key]); check=deepcopy(e)
                cal.parse_dol_report(check,body,calendar["sources"][key]["retrieved_at"])
                verified=(check["actual"],check["previous"],check["reference_period"])==(e["actual"],e["previous"],e["reference_period"])
            except (ValueError,ImportError):
                rejected.append({"source_key":key,"reason":"missing_or_invalid_pinned_source"})
            add(e,"initial_claims_k_sa",e["actual"],e["previous"],key,proof=verified,flags=["preliminary"])
    return {"schema_version":"macro-observations-v1.0.0","parser_version":PARSER_VERSION,
            "calendar_release_id":calendar["release_id"],"calendar_sha256":calendar_sha256,
            "ruleset_sha256":engine.digest(ruleset),"observations":sorted(observations,key=lambda o:(o["metric_id"],o["reference_period"],o["observation_id"])),
            "adapter_exclusions":sorted(rejected,key=lambda r:r["source_key"])}
