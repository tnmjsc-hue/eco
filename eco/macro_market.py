"""Daily market observations, separate from the frozen macro assessment."""
import csv
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import io
import json
from pathlib import Path
import re
import urllib.request
import xml.etree.ElementTree as ET

from .calendar import backup_snapshot
from .macro_pipeline import body, publication_lock, write

ROOT = Path(__file__).resolve().parents[1]
VERSION = "macro-market-v1.0.0"
PROTOCOL_SHA = "2f1920b845406637f13087778d6999af6065a70c3f6ce9a18b8a5c061e008a4d"
FED_BASE = "https://www.federalreserve.gov/datadownload/Output.aspx?"
SOURCES = {
    "fed_yields": FED_BASE + "rel=H15&series=bf17364827e38702b42a58cf8eaa3f78&lastobs=30&filetype=csv&label=include&layout=seriescolumn&type=package",
    "fed_usd": FED_BASE + "rel=H10&series=122e3bcb627e8e53f1bf72a1a09cfb81&lastobs=30&filetype=csv&label=include&layout=seriescolumn&type=package",
}


def utc(value):
    if not isinstance(value, str) or not re.search(r"(?:Z|\+00:00)$", value):
        raise ValueError("invalid UTC timestamp")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.utcoffset().total_seconds() != 0:
        raise ValueError("invalid UTC timestamp")
    return result


def decimal(value):
    if value is None or value in ("ND", "", "."):
        return None
    if not isinstance(value, str) or not re.fullmatch(r"-?\d+(?:\.\d+)?", value):
        raise ValueError("invalid market value")
    try:
        number = Decimal(value)
    except InvalidOperation:
        raise ValueError("invalid market value") from None
    if not number.is_finite():
        raise ValueError("invalid market value")
    return number


def number(value):
    return format(value, "f") if value is not None else None


def calendar_date(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("invalid observation date")
    return date.fromisoformat(value)


def unique_points(points):
    seen = {}
    for day, value in points:
        calendar_date(day)
        decimal(value)
        if day in seen and seen[day] != value:
            raise ValueError("ambiguous daily observation")
        seen[day] = value
    return sorted(seen.items())


def parse_fed(raw, series_id, unit):
    rows = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"))))
    meta = {r[0].strip(): r for r in rows if r}
    headers = meta.get("Time Period", [])
    if headers.count(series_id) != 1:
        raise ValueError("Fed series missing or duplicated")
    index = headers.index(series_id)
    expected = "Percent:_Per_Year" if unit == "percent" else "Index:_1997_Jan_100"
    release = "H15" if unit == "percent" else "H10"
    for key, expected_value in [("Unit:", expected), ("Multiplier:", "1"),
                                ("Unique Identifier:", f"{release}/{release}/{series_id}")]:
        if len(meta.get(key, [])) <= index or meta[key][index] != expected_value:
            raise ValueError("Fed series metadata mismatch")
    points = []
    started = False
    for row in rows:
        if row and row[0] == "Time Period":
            started = True
            continue
        if not started or not row or not any(row):
            continue
        if len(row) != len(headers):
            raise ValueError("truncated Fed row")
        value = decimal(row[index])
        points.append((row[0], number(value)))
    if not points:
        raise ValueError("empty Fed data")
    return unique_points(points)


def parse_real_yield(raw):
    root = ET.fromstring(raw)
    atom = "{http://www.w3.org/2005/Atom}"
    d = "{http://schemas.microsoft.com/ado/2007/08/dataservices}"
    m = "{http://schemas.microsoft.com/ado/2007/08/dataservices/metadata}"
    if root.tag != atom + "feed" or root.findtext(atom + "title") != "DailyTreasuryRealYieldCurveRateData":
        raise ValueError("wrong Treasury feed")
    points = []
    for entry in root.findall(atom + "entry"):
        props = entry.find(atom + "content/" + m + "properties")
        if props is None:
            raise ValueError("missing Treasury properties")
        day = props.findtext(d + "NEW_DATE")
        if not day or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T00:00:00", day):
            raise ValueError("invalid Treasury date")
        values = props.findall(d + "TC_10YEAR")
        if len(values) != 1:
            raise ValueError("missing Treasury real 10y series")
        value = values[0]
        points.append((day[:10], None if value.get(m + "null") == "true" else number(decimal(value.text))))
    if not points:
        raise ValueError("empty Treasury data")
    return unique_points(points)


def measure(metric_id, points, source, as_of, protocol):
    cutoff = utc(as_of)
    usable_at = source.get("usable_at", source.get("retrieved_at"))
    if utc(usable_at) > cutoff or source.get("retrieved_at") and utc(source["retrieved_at"]) > cutoff:
        raise ValueError("future source retrieval")
    spec = protocol["metrics"][metric_id]
    rows = [(d, decimal(v)) for d, v in unique_points(points) if calendar_date(d) < cutoff.date()]
    result = {"metric_id": metric_id, **spec, "status": "unavailable", "reason": "missing_pair",
              "latest": None, "previous": None, "latest_date": None, "previous_date": None,
              "change": None, "source": source}
    if not rows:
        return result
    day, latest = rows[-1]
    result.update(latest_date=day, latest=number(latest))
    if latest is None:
        result["reason"] = "missing_latest_value"
        return result
    prior = [(d, v) for d, v in rows[:-1] if v is not None]
    if not prior:
        return result
    prev_day, previous = prior[-1]
    result.update(previous_date=prev_day, previous=number(previous))
    if (calendar_date(day) - calendar_date(prev_day)).days > protocol["maximum_pair_gap_days"]:
        result["reason"] = "pair_gap"
        return result
    if spec["change_unit"] == "percent" and (previous <= 0 or latest <= 0):
        result["reason"] = "invalid_price_or_index"
        return result
    change = (latest - previous) * 100 if spec["change_unit"] == "bps" else (latest / previous - 1) * 100
    age = (cutoff.date() - calendar_date(day)).days
    result.update(change=number(change), status="stale" if age > spec["max_age_days"] else "measured",
                  reason="observation_expired" if age > spec["max_age_days"] else None)
    return result


def checked_asset(root, record, pattern):
    url = record.get("url", record.get("manifest_url", ""))
    if not re.fullmatch(pattern, url):
        raise ValueError("invalid market parent path")
    raw = (root / "public" / url.lstrip("/")).read_bytes()
    expected = record.get("sha256", record.get("manifest_sha256"))
    if sha256(raw).hexdigest() != expected:
        raise ValueError("market parent checksum mismatch")
    return json.loads(raw)


def eth_input(root, as_of, protocol):
    pointer = json.loads((root / "public/data/core-v2/latest.json").read_bytes())
    pattern = r"/data/core-v2/releases/core10-[a-f0-9]{20}/manifest\.json"
    manifest = checked_asset(root, pointer, pattern)
    if manifest["release_id"] != pointer["release_id"] or manifest.get("asset") != "eth" or manifest.get("attribution", {}).get("licence") != "CC BY-NC 4.0":
        raise ValueError("unapproved ETH parent")
    history_record = {"url": pointer["manifest_url"].replace("manifest.json", "history.json"), "sha256": manifest["files"]["history.json"]}
    history = checked_asset(root, history_record, pattern.replace("manifest", "history"))
    if history.get("asset") != "eth" or history["release_id"] != manifest["release_id"]:
        raise ValueError("ETH history lineage mismatch")
    if utc(manifest["computed_at"]) > utc(as_of):
        raise ValueError("future ETH parent")
    points = []
    for row in history["rows"]:
        value = row["price_usd"]
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not row["period_closed_at_retrieval"]):
            raise ValueError("invalid ETH daily price")
        points.append((row["date"], str(value) if value is not None else None))
    source = {"provider": "coinmetrics", "url": "https://gitbook-docs.coinmetrics.io/packages/coin-metrics-community-data",
              "sha256": history_record["sha256"], "retrieved_at": None, "usable_at": manifest["computed_at"],
              "knowledge_basis": "verified_parent_computed_at", "licence": "CC BY-NC 4.0"}
    return measure("eth_usd", points, source, as_of, protocol), {"manifest": {"url": pointer["manifest_url"], "sha256": pointer["manifest_sha256"]}, "history": history_record}


def fetch_source(root, key, url, now):
    path = root / "data/raw/macro-market/cache" / (key + ".json")
    previous = json.loads(path.read_bytes()) if path.exists() else None
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 ECO noncommercial research", "Accept": "text/csv,application/xml"})
    with urllib.request.urlopen(request, timeout=40) as response:
        if response.url != url:
            raise ValueError("unexpected provider redirect")
        raw = response.read(4_000_001)
    if len(raw) > 4_000_000:
        raise ValueError("oversized market response")
    digest = sha256(raw).hexdigest()
    if previous and previous.get("url") == url and previous.get("sha256") == digest:
        if sha256(previous["body"].encode()).hexdigest() != digest or utc(previous["retrieved_at"]) > now:
            raise ValueError("invalid market cache")
        return previous
    value = {"url": url, "sha256": digest, "retrieved_at": now.isoformat(), "body": raw.decode("utf-8")}
    write(path, value)
    return value


def publish(root, inputs, protocol, snapshot, receipt, as_of):
    folder = root / "public/data/macro-market"
    with publication_lock(folder):
        input_sha = sha256(body(inputs)).hexdigest()
        protocol_sha = sha256(body(protocol)).hexdigest()
        identity = {"input_sha256": input_sha, "protocol_sha256": protocol_sha}
        prior_path = folder / "latest.json"
        prior = json.loads(prior_path.read_bytes()) if prior_path.exists() else None
        prior_manifest = None
        if prior:
            previous = checked_asset(root, prior, r"/data/macro-market/releases/market-[a-f0-9]{20}/market\.json")
            if previous["release_id"] != prior["release_id"] or utc(previous["generated_at"]) > utc(as_of):
                raise ValueError("future or mismatched market predecessor")
            prior_manifest = checked_asset(root, prior["manifest"], r"/data/macro-market/releases/market-[a-f0-9]{20}/manifest\.json")
            if prior_manifest["release_id"] != prior["release_id"]:
                raise ValueError("market predecessor lineage mismatch")
            for name in ("inputs", "protocol"):
                if prior_manifest[name]["url"] != f'/data/macro-market/releases/{prior["release_id"]}/{name}.json':
                    raise ValueError("market predecessor input mismatch")
                checked_asset(root, prior_manifest[name], r"/data/macro-market/releases/market-[a-f0-9]{20}/(?:inputs|protocol)\.json")
        if prior_manifest and prior_manifest["inputs"]["sha256"] == input_sha and prior_manifest["protocol"]["sha256"] == protocol_sha:
            write(folder / "status.json", {"outcome": "unchanged", "checked_at": as_of, "release_id": prior["release_id"], "last_good_retained": True})
            return {"outcome": "unchanged", "release_id": prior["release_id"]}
        if prior:
            identity["previous_release_id"] = prior["release_id"]
        release_id = "market-" + sha256(body(identity)).hexdigest()[:20]
        if not receipt or any(x.get("readback_verified") is not True for x in receipt):
            raise ValueError("unverified private market backup")
        # Require complete backup of all snapshot files, not an arbitrary true flag.
        expected = {p.name: sha256(p.read_bytes()).hexdigest() for p in snapshot.iterdir()}
        actual = {x["object_key"].rsplit("/", 1)[-1]: x["sha256"] for x in receipt}
        if expected != actual or len(receipt) != len(expected) or any(x["object_key"] != f'raw/macro-market/{snapshot.name}/{x["object_key"].rsplit("/", 1)[-1]}' for x in receipt):
            raise ValueError("incomplete private market backup")
        base = f"/data/macro-market/releases/{release_id}"
        release = folder / "releases" / release_id
        value = {"schema_version": VERSION, "release_id": release_id, "generated_at": as_of,
                 "comparison_basis": "daily_change", "metrics": inputs["metrics"],
                 "consensus": {"status": "unavailable", "reason": "no_approved_pre_release_consensus"},
                 "event_reaction": {"status": "not_measured", "reason": "no_verified_intraday_window"}}
        # An interrupted publication can reuse its original artifact, never rewrite it.
        if (release / "market.json").exists():
            saved = json.loads((release / "market.json").read_bytes())
            if {k: v for k, v in saved.items() if k != "generated_at"} != {k: v for k, v in value.items() if k != "generated_at"} or utc(saved["generated_at"]) > utc(as_of):
                raise ValueError("immutable market collision")
            value = saved
        write(release / "market.json", value, True)
        write(release / "inputs.json", inputs, True)
        write(release / "protocol.json", protocol, True)
        manifest = {"schema_version": VERSION, "release_id": release_id,
                    "inputs": {"url": base + "/inputs.json", "sha256": input_sha},
                    "protocol": {"url": base + "/protocol.json", "sha256": protocol_sha},
                    "eth_parent": inputs["eth_parent"], "private_backup": {"verified": True, "snapshot_id": snapshot.name, "objects": receipt},
                    "previous_release_id": prior["release_id"] if prior else None}
        if (release / "manifest.json").exists():
            saved = json.loads((release / "manifest.json").read_bytes())
            if any(saved[k] != manifest[k] for k in ("inputs", "protocol", "eth_parent", "previous_release_id")):
                raise ValueError("immutable market manifest collision")
            manifest = saved
        write(release / "manifest.json", manifest, True)
        pointer = {"schema_version": VERSION, "release_id": release_id, "url": base + "/market.json",
                   "sha256": sha256((release / "market.json").read_bytes()).hexdigest(),
                   "manifest": {"url": base + "/manifest.json", "sha256": sha256((release / "manifest.json").read_bytes()).hexdigest()}}
        write(prior_path, pointer)
        write(folder / "status.json", {"outcome": "published", "checked_at": as_of, "release_id": release_id, "last_good_retained": False})
        return {"outcome": "published", "release_id": release_id}


def run(root=ROOT, now=None):
    root = Path(root)
    now = now or datetime.now(timezone.utc)
    as_of = now.isoformat()
    utc(as_of)
    protocol = json.loads((root / f"configs/macro/{VERSION}.json").read_bytes())
    if sha256(body(protocol)).hexdigest() != PROTOCOL_SHA:
        raise ValueError("market protocol changed under frozen version")
    sources = {}
    urls = {**SOURCES, "treasury_real": "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml?data=daily_treasury_real_yield_curve&field_tdr_date_value=" + str(now.year)}
    try:
        # In January request the previous year as well so the first pair spans New Year.
        if now.month == 1:
            urls["treasury_real_prior"] = urls["treasury_real"].replace(str(now.year), str(now.year - 1))
        for key, url in urls.items():
            sources[key] = fetch_source(root, key, url, now)
        metrics = []
        for metric in ("treasury_2y", "treasury_10y", "usd_broad", "real_yield_10y"):
            spec = protocol["metrics"][metric]
            key = "fed_usd" if metric == "usd_broad" else "treasury_real" if metric == "real_yield_10y" else "fed_yields"
            raw = sources[key]["body"].encode()
            points = parse_real_yield(raw) if key == "treasury_real" else parse_fed(raw, spec["series_id"], spec["unit"])
            source = {"provider": spec["provider"], **{k: sources[key][k] for k in ("url", "sha256", "retrieved_at")},
                      "usable_at": sources[key]["retrieved_at"], "knowledge_basis": "source_retrieved_at", "licence": "US_government_public_domain"}
            if key == "treasury_real" and "treasury_real_prior" in sources:
                prior = sources["treasury_real_prior"]
                points += parse_real_yield(prior["body"].encode())
                source["prior_year"] = {k: prior[k] for k in ("url", "sha256", "retrieved_at")}
            metrics.append(measure(metric, points, source, as_of, protocol))
        eth, parent = eth_input(root, as_of, protocol)
        metrics.append(eth)
        metrics.append({"metric_id": "gold_usd", **protocol["metrics"]["gold_usd"], "status": "unavailable",
                        "reason": "no_approved_gold_source", "latest": None, "previous": None,
                        "latest_date": None, "previous_date": None, "change": None, "source": None})
        inputs = {"protocol_version": VERSION, "metrics": metrics, "eth_parent": parent}
        snapshot = root / "data/raw/macro-market" / (now.strftime("%Y%m%dT%H%M%S%fZ") + "-" + sha256(body(inputs)).hexdigest()[:12])
        snapshot.mkdir(parents=True)
        for key, source in sources.items():
            write(snapshot / (key + ".json"), source, True)
        write(snapshot / "normalized.json", inputs, True)
        write(snapshot / "manifest.json", {"protocol_version": VERSION, "retrieved_at": as_of,
              "files": {p.name: sha256(p.read_bytes()).hexdigest() for p in snapshot.iterdir()}}, True)
        receipt = backup_snapshot(snapshot, prefix="macro-market")
        return publish(root, inputs, protocol, snapshot, receipt, as_of)
    except Exception:
        write(root / "public/data/macro-market/status.json", {"outcome": "error", "checked_at": as_of,
              "last_good_retained": (root / "public/data/macro-market/latest.json").exists(), "reason": "source_or_verification_failed"})
        raise


if __name__ == "__main__":
    try:
        print(json.dumps(run()))
    except Exception:
        # Provider errors must not print request URLs, credentials or raw responses.
        raise SystemExit("Market batch failed; last verified release retained") from None
