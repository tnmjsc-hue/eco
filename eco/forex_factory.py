"""Fetch and publish verified Forex Factory calendar snapshots without changing macro inputs."""

import argparse
from datetime import date, datetime, timedelta
import gzip
import html
import json
from pathlib import Path
import re
import urllib.request

from .calendar import ROOT, UTC, backup_snapshot, digest, encode, retry_transient, safe_failure_code, stamp, write_json

SOURCE = "https://calendar.forexfactory.com/calendar"
VERSION = "forex-factory-calendar-v1.0.0"
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
IMPACTS = {"low", "medium", "high", "holiday"}
HASH = r"[a-f0-9]{64}"
RELEASE = r"ff-calendar-[a-f0-9]{20}"
MAX_BODY_BYTES = 8_000_000


class ForexFactoryError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def range_url(start, end):
    def part(day):
        return f"{MONTHS[day.month - 1].lower()}{day.day}.{day.year}"
    return f"{SOURCE}?range={part(start)}-{part(end)}"


def fetch_calendar(url):
    request = urllib.request.Request(url, headers={"User-Agent": "ECO-economic-calendar/1.0 (+https://eco.tnmp.cloud/)"})

    def load():
        with urllib.request.urlopen(request, timeout=25) as response:
            if response.url != url or response.headers.get_content_type() != "text/html":
                raise ForexFactoryError("unexpected_response", "unexpected Forex Factory response")
            body = response.read(MAX_BODY_BYTES + 1)
            if not body or len(body) > MAX_BODY_BYTES:
                raise ForexFactoryError("invalid_body_size", "Forex Factory response size invalid")
            return body, response.headers.get_content_charset() or "utf-8"

    return retry_transient(load)


def clean_text(value, limit):
    if not isinstance(value, str):
        raise ForexFactoryError("invalid_event_text", "invalid event text")
    value = " ".join(html.unescape(value).split())
    if len(value) > limit:
        raise ForexFactoryError("event_text_limit", "event text exceeded limit")
    return value


def source_value(value):
    value = clean_text(value, 80)
    return None if value in {"", "—", "-"} else value


def parse_calendar(body, charset, start, end):
    page = body.decode(charset)
    anchor = re.search(r"window\.calendarComponentStates\[1\]\s*=\s*\{\s*days:\s*(?=\[)", page)
    if not anchor:
        raise ForexFactoryError("calendar_state_missing", "Forex Factory calendar state missing")
    days, _ = json.JSONDecoder().raw_decode(page, anchor.end())
    day_count = (end - start).days + 1
    if len(days) != day_count:
        raise ForexFactoryError("date_coverage_mismatch", "Forex Factory date coverage mismatch")
    events = []
    ids = set()
    for offset, entry in enumerate(days):
        day = start + timedelta(days=offset)
        month = MONTHS[day.month - 1]
        if not re.fullmatch(rf"[A-Za-z]{{3}} <span>{month} {day.day}</span>", entry["date"]):
            raise ForexFactoryError("date_coverage_mismatch", "Forex Factory date coverage mismatch")
        day_epoch = entry["dateline"]
        next_epoch = days[offset + 1]["dateline"] if offset + 1 < day_count else day_epoch + 25 * 3600
        if type(day_epoch) is not int or type(next_epoch) is not int or next_epoch - day_epoch not in {23 * 3600, 24 * 3600, 25 * 3600}:
            raise ForexFactoryError("invalid_day_boundary", "invalid calendar day boundary")
        for row in entry["events"]:
            event_id = row["id"]
            currency = row["currency"]
            title = clean_text(row["name"], 180)
            impact = row["impactName"]
            event_epoch = row["dateline"]
            masked = row["timeMasked"]
            expects_actual = row["hasDataValues"]
            if (type(event_id) is not int or event_id <= 0 or event_id in ids
                    or not re.fullmatch(r"[A-Z]{3}|All", currency)
                    or impact not in IMPACTS or not title
                    or type(masked) is not bool or type(expects_actual) is not bool or type(row["leaked"]) is not bool
                    or type(event_epoch) is not int):
                raise ForexFactoryError("invalid_event", "invalid or duplicate Forex Factory event")
            if not day_epoch <= event_epoch < next_epoch:
                raise ForexFactoryError("event_outside_day", "Forex Factory event epoch is outside its calendar day")
            if row["date"] != f"{month} {day.day}, {day.year}":
                raise ForexFactoryError("event_date_mismatch", "Forex Factory event date does not match its calendar day")
            ids.add(event_id)
            actual = source_value(row["actual"])
            previous = source_value(row["previous"])
            revised = source_value(row["revision"])
            solo = row["soloUrl"]
            events.append({
                "id": event_id,
                "title": title,
                "currency": currency,
                "impact": impact,
                "source_day": day.isoformat(),
                "scheduled_at": None if masked else stamp(datetime.fromtimestamp(event_epoch, UTC)),
                "time_label": clean_text(row["timeLabel"], 48) if masked else None,
                "expects_actual": expects_actual,
                "actual": None if row["leaked"] else actual,
                "forecast": source_value(row["forecast"]),
                "previous": revised if revised is not None else previous,
                "previous_initial": previous if revised is not None and revised != previous else None,
                "source_path": solo if re.fullmatch(r"/calendar/[0-9]+-[a-z0-9-]+", solo) else None,
            })
    table_ids = re.findall(r'<tr\b[^>]*\bdata-event-id="(\d+)"', page)
    if not events or len(table_ids) != len(events) or {int(event_id) for event_id in table_ids} != ids:
        raise ForexFactoryError("visible_rows_mismatch", "embedded state did not match visible calendar rows")
    return events


def read_latest(public):
    file = public / "latest.json"
    if not file.exists():
        return None
    pointer = json.loads(file.read_bytes())
    release = pointer["release_id"]
    if (not re.fullmatch(RELEASE, release) or not re.fullmatch(HASH, pointer["sha256"])
            or not re.fullmatch(HASH, pointer["content_sha256"])
            or pointer["url"] != f"/data/forex-factory/releases/{release}/calendar.json"):
        raise ForexFactoryError("invalid_pointer", "invalid Forex Factory publication pointer")
    body = (public / "releases" / release / "calendar.json").read_bytes()
    if digest(body) != pointer["sha256"]:
        raise ForexFactoryError("invalid_pointer_checksum", "Forex Factory publication checksum mismatch")
    data = json.loads(body)
    if data["calendar_version"] != VERSION or data["content_sha256"] != pointer["content_sha256"]:
        raise ForexFactoryError("invalid_pointer_version", "Forex Factory publication version mismatch")
    return pointer


def run_batch(root=ROOT, today=None):
    started = datetime.now(UTC)
    today = today or (started + timedelta(hours=7)).date()
    start, end = today - timedelta(days=30), today + timedelta(days=30)
    public = root / "public/data/forex-factory"
    stage = "verify_previous"
    try:
        last = read_latest(public)
        url = range_url(start, end)
        stage = "fetch"
        raw, charset = fetch_calendar(url)
        retrieved_at = stamp(datetime.now(UTC))
        stage = "parse"
        events = parse_calendar(raw, charset, start, end)
        content = {"coverage_start": start.isoformat(), "coverage_end": end.isoformat(), "events": events}
        content_hash = digest(encode(content))
        if last and content_hash == last["content_sha256"]:
            release_id = last["release_id"]
        else:
            stage = "prepare_backup"
            source = {"url": url, "sha256": digest(raw), "charset": charset, "retrieved_at": retrieved_at,
                      "media_type": "text/html"}
            revision_of = last["release_id"] if last else None
            run_id = digest(encode({"source": source, "content": content_hash, "revision_of": revision_of}))[:20]
            release_id = f"ff-calendar-{run_id}"
            folder = root / "data/raw/forex-factory" / release_id
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "calendar.html.gz").write_bytes(gzip.compress(raw, mtime=0))
            write_json(folder / "calendar.json", content, immutable=True)
            write_json(folder / "manifest.json", {"calendar_version": VERSION, "source": source,
                                                   "raw_compression": "gzip",
                                                   "raw_gzip_sha256": digest((folder / "calendar.html.gz").read_bytes()),
                                                   "content_sha256": content_hash}, immutable=True)
            stage = "verify_backup"
            backup = backup_snapshot(folder, prefix="forex-factory")
            stage = "publish"
            report = {**content, "calendar_version": VERSION, "release_id": release_id, "source": source,
                      "content_sha256": content_hash, "revision_of": revision_of, "private_backup": backup}
            report_file = public / "releases" / release_id / "calendar.json"
            write_json(report_file, report, immutable=True)
            write_json(public / "latest.json", {"release_id": release_id, "sha256": digest(report_file.read_bytes()),
                                                "content_sha256": content_hash,
                                                "url": f"/data/forex-factory/releases/{release_id}/calendar.json"})
        stage = "report_status"
        write_json(public / "status.json", {"outcome": "ok", "release_id": release_id,
                                          "last_success_at": retrieved_at})
        return {"release_id": release_id, "rows": len(events), "actuals": sum(e["actual"] is not None for e in events)}
    except Exception as exc:
        reason = exc.code if isinstance(exc, ForexFactoryError) else safe_failure_code(exc)
        write_json(public / "status.json", {"outcome": "error", "last_attempt_at": stamp(started),
                                          "failure_stage": stage, "failure_code": reason})
        raise ValueError(f"Forex Factory refresh failed during {stage}: {reason}") from None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--today", type=date.fromisoformat, help="Override the Vietnam calendar date")
    args = parser.parse_args()
    print(json.dumps(run_batch(today=args.today)))
