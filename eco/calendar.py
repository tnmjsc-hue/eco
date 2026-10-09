"""Official US macro calendar; cached batch, private snapshots, static publication."""
import argparse
import base64
import calendar as month_names
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import html
import hmac
import io
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
UTC = timezone.utc
VERSION = "us-macro-calendar-v1.1.0"
SOURCES = {
    "bls": "https://www.bls.gov/schedule/news_release/bls.ics",
    "bea": "https://www.bea.gov/news/schedule/ics/online-calendar-subscription.ics",
    "fed": "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
    "bls_data": "https://api.bls.gov/publicAPI/v2/timeseries/data/",
    "bea_schedule": "https://www.bea.gov/news/schedule/full",
    "fed_calendar": "https://www.federalreserve.gov/newsevents/calendar.htm",
    "dol_schedule": "https://oui.doleta.gov/unemploy/claims_arch.asp",
}
SERIES = {
    "cpi": ("CUSR0000SA0", "CPI m/m", "percent", "change_percent"),
    "payrolls": ("CES0000000001", "Nonfarm payrolls", "thousand_jobs", "change"),
    "unemployment": ("LNS14000000", "Unemployment rate", "percent", "level"),
    "ppi": ("WPSFD4", "PPI final demand m/m", "percent", "change_percent"),
    "jolts": ("JTS000000000000000JOL", "JOLTS job openings", "thousand_jobs", "level"),
}
RULES = [
    ("Consumer Price Index", "cpi", "CPI · lạm phát tiêu dùng", "high", "inflation"),
    ("Employment Situation", "jobs", "NFP · việc làm và thất nghiệp", "high", "labor"),
    ("Producer Price Index", "ppi", "PPI · giá sản xuất", "high", "inflation"),
    ("Job Openings and Labor Turnover", "jolts", "JOLTS · việc làm còn trống", "medium", "labor"),
    ("Employment Cost Index", "eci", "ECI · chi phí lao động", "medium", "inflation"),
    ("Productivity and Costs", "productivity", "Năng suất và chi phí lao động", "medium", "growth"),
    ("U.S. Import and Export Price", "trade_prices", "Giá xuất nhập khẩu Mỹ", "medium", "inflation"),
    ("Real Earnings", "real_earnings", "Thu nhập thực Mỹ", "medium", "labor"),
    ("Usual Weekly Earnings", "weekly_earnings", "Thu nhập tuần của lao động Mỹ", "medium", "labor"),
    ("Employer Costs for Employee Compensation", "employer_costs", "Chi phí nhân công", "medium", "inflation"),
    ("Quarterly Data Series on Business Employment Dynamics", "business_employment", "Biến động việc làm doanh nghiệp", "medium", "labor"),
    ("Current Employment Statistics Preliminary Benchmark (National)", "jobs_benchmark", "Điều chỉnh chuẩn việc làm", "medium", "labor"),
    ("Personal Income and Outlays", "pce", "PCE · thu nhập và chi tiêu", "high", "inflation"),
    ("Gross Domestic Product,", "gdp", "GDP Mỹ", "high", "growth"),
    ("GDP (", "gdp", "GDP Mỹ", "high", "growth"),
    ("U.S. International Trade in Goods and Services", "trade", "Cán cân thương mại Mỹ", "medium", "growth"),
    ("U.S. International Transactions", "international_transactions", "Giao dịch quốc tế Mỹ", "medium", "growth"),
    ("U.S. International Investment Position", "investment_position", "Vị thế đầu tư quốc tế Mỹ", "medium", "growth"),
]

def stamp(value):
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")

def digest(body):
    return hashlib.sha256(body).hexdigest()

def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()

def write_json(path, value, immutable=False):
    body = encode(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    if immutable and path.exists():
        if path.read_bytes() != body:
            raise ValueError("immutable calendar artifact changed")
        return
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_bytes(body)
    temp.replace(path)

def parse_ics(body, provider):
    # BEA uses CRCRLF and folds long summaries; normalize before unfolding.
    text = body.decode("utf-8-sig").replace("\r", "")
    text = re.sub(r"\n[ \t]", "", text)
    if "BEGIN:VCALENDAR" not in text or "END:VCALENDAR" not in text:
        raise ValueError("incomplete official calendar")
    events = []
    for block in re.findall(r"BEGIN:VEVENT\n(.*?)END:VEVENT", text, re.S):
        props = {}
        for line in block.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                props[key.split(";")[0]] = (key, value)
        title = props.get("SUMMARY", ("", ""))[1].replace(r"\,", ",").replace(r"\;", ";").strip()
        rule = next((r for r in RULES if title.startswith(r[0])), None)
        if not rule:
            continue
        key, raw = props["DTSTART"]
        if raw.endswith("Z"):
            when = datetime.strptime(raw, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
        elif "TZID=US-Eastern" in key or "TZID=America/New_York" in key:
            when = datetime.strptime(raw, "%Y%m%dT%H%M%S").replace(tzinfo=ZoneInfo("America/New_York"))
        else:
            raise ValueError("unsupported calendar timezone")
        events.append(event(provider, rule[1], rule[2], title, when, rule[3], rule[4], SOURCES[provider]))
    if len(events) < 10:
        raise ValueError("official calendar lost expected coverage")
    return events

def event(provider, kind, label, original, when, impact, category, source):
    return {"id": f"{provider}-{kind}-{when.date()}", "provider": provider, "kind": kind,
            "title": label, "source_title": original, "scheduled_at": stamp(when),
            "currency": "USD", "country": "US", "impact": impact, "category": category,
            "source_url": source, "actual": None, "forecast": None, "previous": None,
            "unit": None, "reference_period": None, "data_status": "scheduled",
            "data_source_url": None, "data_vintage_at": None, "details": []}

def plain(text):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]*>", " ", text))).strip()

def parse_fed(body):
    text = body.decode()
    events = []
    panels = re.split(r"(\d{4}) FOMC Meetings", text)
    for index in range(1, len(panels), 2):
        year, panel = int(panels[index]), panels[index + 1]
        count = 0
        for block in re.split(r'<div class="[^"]*row fomc-meeting[^\"]*"', panel)[1:]:
            month = re.search(r'fomc-meeting__month[^>]*>\s*<strong>(.*?)</strong>', block, re.S)
            days = re.search(r'fomc-meeting__date[^>]*>(.*?)</div>', block, re.S)
            if not month or not days:
                continue
            month = plain(month[1]).split("/")[-1]
            abbreviations = {name: i for i, name in enumerate(month_names.month_abbr) if name}
            if month in abbreviations:
                month = month_names.month_name[abbreviations[month]]
            if month not in list(month_names.month_name):
                raise ValueError("unsupported FOMC month")
            # Unscheduled notation votes are not scheduled policy decisions.
            raw_days = plain(days[1])
            if "notation" in raw_days:
                continue
            day = int(re.findall(r"\d+", raw_days)[-1])
            when = datetime(year, list(month_names.month_name).index(month), day, 14,
                            tzinfo=ZoneInfo("America/New_York"))
            e = event("fed", "fomc", "FOMC · quyết định lãi suất", f"FOMC {year} {month} {raw_days}",
                      when, "high", "policy", SOURCES["fed"])
            e["time_basis"] = "standard_14_et_verify_with_statement"
            links = re.findall(r'href="([^"]*monetary\d{8}a.htm)"', block)
            if links:
                e["source_url"] = urllib.parse.urljoin(SOURCES["fed"], links[0])
            events.append(e)
            count += 1
        if count < 7:
            raise ValueError("FOMC schedule coverage changed")
    if not events:
        raise ValueError("FOMC parser found no meetings")
    return events

def previous_month(period):
    year, month = map(int, period.split("-"))
    return f"{year - (month == 1):04d}-{12 if month == 1 else month - 1:02d}"

def parse_indicators(body):
    payload = json.loads(body)
    if payload.get("status") != "REQUEST_SUCCEEDED":
        raise ValueError("BLS API did not succeed")
    source = {s["seriesID"]: s["data"] for s in payload["Results"]["series"]}
    indicators = []
    for key, (sid, title, unit, mode) in SERIES.items():
        values = {f'{r["year"]}-{r["period"][1:]}': Decimal(r["value"]) for r in source.get(sid, [])
                  if re.fullmatch(r"M(0[1-9]|1[0-2])", r["period"]) and re.fullmatch(r"-?\d+(\.\d+)?", r["value"])}
        if not values:
            raise ValueError("BLS API series missing")
        period = max(values)
        def value_at(p):
            if p not in values:
                return None
            if mode == "level":
                return float(values[p])
            prior = values.get(previous_month(p))
            if prior is None or (mode == "change_percent" and prior <= 0):
                return None
            result = values[p] - prior if mode == "change" else (values[p] / prior - 1) * 100
            return float(result.quantize(Decimal("0.1")))
        footnotes = next(r.get("footnotes", []) for r in source[sid] if f'{r["year"]}-{r["period"][1:]}' == period)
        indicators.append({"id": key, "series_id": sid, "title": title, "unit": unit,
                           "reference_period": period, "value": value_at(period),
                           "previous_period": previous_month(period), "previous": value_at(previous_month(period)),
                           "preliminary": any(n.get("code") == "P" for n in footnotes),
                           "source_url": f"https://data.bls.gov/timeseries/{sid}", "seasonally_adjusted": True})
    return indicators


def attach_bls_results(events, indicators, now, retrieved_at):
    """Join only the latest completed release of each series to its latest API period.

    This is a current-vintage period match, never an as-published historical value.
    """
    by_id = {row["id"]: row for row in indicators}
    for kind, series_id in [("cpi", "cpi"), ("jobs", "payrolls"), ("ppi", "ppi"), ("jolts", "jolts")]:
        past = [e for e in events if e["provider"] == "bls" and e["kind"] == kind
                and datetime.fromisoformat(e["scheduled_at"].replace("Z", "+00:00")) < now]
        if not past:
            continue
        e = max(past, key=lambda row: row["scheduled_at"])
        row = by_id[series_id]
        when = datetime.fromisoformat(e["scheduled_at"].replace("Z", "+00:00"))
        period = row["reference_period"]
        lag = (when.year - int(period[:4])) * 12 + when.month - int(period[5:])
        if not 0 <= lag <= 3 or row["value"] is None or row["previous"] is None:
            continue
        e.update(actual=row["value"], previous=row["previous"], unit=row["unit"],
                 reference_period=period, data_status="current_vintage_period_match",
                 data_source_url=row["source_url"], data_vintage_at=retrieved_at)
        if kind == "jobs":
            unemployment = by_id["unemployment"]
            if unemployment["reference_period"] == period:
                e["details"].append({"label": "Tỷ lệ thất nghiệp", "actual": unemployment["value"],
                                     "previous": unemployment["previous"], "unit": "percent"})


def parse_bea_schedule(body):
    page = body.decode("utf-8-sig")
    if "scheduled-releases-type-press" not in page:
        raise ValueError("BEA release index lost expected rows")
    releases = {}
    for block in re.findall(r'<tr class="scheduled-releases-type-press">(.*?)</tr>', page, re.S):
        title = re.search(r'<td class="release-title[^>]*>(.*?)</td>', block, re.S)
        link = re.search(r'href="(/news/\d{4}/[a-zA-Z0-9/_-]+)"', block)
        if title and link:
            releases[plain(title[1])] = urllib.parse.urljoin("https://www.bea.gov", link[1])
    if len(releases) < 20:
        raise ValueError("BEA release index coverage changed")
    return releases


def parse_bea_report(e, body, retrieved_at):
    report = plain(body.decode("utf-8-sig", errors="replace"))
    if e["source_title"] not in report or "EMBARGOED UNTIL RELEASE" not in report:
        raise ValueError("BEA report does not match scheduled title")
    title = e["source_title"]
    if e["kind"] == "pce":
        month = re.search(r'Personal Income and Outlays, (\w+) \d{4}', title)
        if not month:
            return
        headline = re.search(rf'PCE price index for {month[1]} (increased|decreased) ([\d.]+) percent', report)
        table = re.search(r'PCE price index\s+(-?[\d.]+)\s+(-?[\d.]+)\s+PCE price index excluding food and energy\s+(-?[\d.]+)\s+(-?[\d.]+)', report)
        if not headline or not table or abs(float(headline[2]) * (1 if headline[1] == "increased" else -1) - float(table[2])) > 0.01:
            return
        e.update(actual=float(table[2]), previous=float(table[1]), unit="percent")
        # The source title supplies the exact observation month, separately from the release date.
        period = re.search(r'([A-Za-z]+) (\d{4})$', title)
        e["reference_period"] = f'{period[2]}-{list(month_names.month_name).index(period[1]):02d}'
        e["details"].append({"label": "Core PCE m/m", "actual": float(table[4]),
                             "previous": float(table[3]), "unit": "percent"})
    elif e["kind"] == "trade":
        match = re.search(r'goods and services deficit was \$([\d.]+) billion in \w+,.*?from \$([\d.]+) billion in \w+', report)
        period = re.search(r'([A-Za-z]+) (\d{4})$', title)
        if not match or not period:
            return
        e.update(actual=-float(match[1]), previous=-float(match[2]), unit="billion_usd",
                 reference_period=f'{period[2]}-{list(month_names.month_name).index(period[1]):02d}')
    elif e["kind"] == "gdp":
        match = re.search(r'Real gross domestic product \(GDP\) (increased|decreased) at an annual rate of ([\d.]+) percent in the (\w+) quarter of (\d{4}).*?In the (?:first|second|third|fourth) quarter, real GDP (increased|decreased) ([\d.]+) percent', report, re.I)
        if not match:
            return
        quarter = {"first": 1, "second": 2, "third": 3, "fourth": 4}.get(match[3].lower())
        if quarter is None:
            return
        e.update(actual=float(match[2]) * (1 if match[1].lower() == "increased" else -1),
                 previous=float(match[6]) * (1 if match[5].lower() == "increased" else -1),
                 unit="percent_saar", reference_period=f'{match[4]}-Q{quarter}')
    else:
        return
    e.update(data_status="official_release", data_source_url=e["source_url"], data_vintage_at=retrieved_at)


def parse_fed_month(body, year, month, source_url):
    page = body.decode("utf-8-sig").replace("\r", "")
    headings = list(re.finditer(r'<div class="row cal-nojs__rowTitle"[^>]*>\s*<h4[^>]*>(.*?)</h4>', page, re.S))
    if len(headings) < 3:
        raise ValueError("Fed monthly calendar structure changed")
    choices = {"FOMC Minutes": ("minutes", "FOMC · biên bản họp", "medium", "policy"),
               "Beige Book": ("beige_book", "Fed Beige Book", "medium", "growth"),
               "G.17 - Industrial Production and Capacity Utilization": ("industrial_production", "Sản lượng công nghiệp Mỹ", "medium", "growth"),
               "G.19 - Consumer Credit": ("consumer_credit", "Tín dụng tiêu dùng Mỹ", "medium", "growth")}
    events = []
    for index, heading in enumerate(headings):
        section = plain(heading[1])
        if section not in ["FOMC Meetings", "Beige Book", "Statistical Releases"]:
            continue
        segment = page[heading.end():headings[index + 1].start() if index + 1 < len(headings) else len(page)]
        for match in re.finditer(r'<div class="col-xs-2">\s*<p>(.*?)</p>.*?<div class="col-xs-7">\s*<p>(.*?)</p>.*?<div class="col-xs-3">\s*<p>(.*?)</p>', segment, re.S):
            time_text, title, day_text = (plain(part) for part in match.groups())
            choice = choices.get(title)
            clock = re.fullmatch(r'(\d{1,2}):(\d{2}) (a\.m\.|p\.m\.)', time_text)
            if not choice or not clock or not re.fullmatch(r'\d{1,2}', day_text):
                continue
            hour = int(clock[1]) % 12 + (12 if clock[3] == "p.m." else 0)
            when = datetime(year, month, int(day_text), hour, int(clock[2]), tzinfo=ZoneInfo("America/New_York"))
            events.append(event("fed", choice[0], choice[1], title, when, choice[2], choice[3], source_url))
    return events


def fed_month_urls(body, start, end):
    page = body.decode("utf-8-sig")
    candidates = re.findall(r'href="(/newsevents/(\d{4})-([a-z]+)\.htm)"', page)
    urls = {}
    for path, year, month_name in candidates:
        month = next((i for i, name in enumerate(month_names.month_name) if name.lower() == month_name), None)
        if month is None:
            continue
        first = datetime(int(year), month, 1, tzinfo=UTC)
        if first.replace(day=28) + timedelta(days=4) >= start and first <= end:
            urls[f"fed_month_{year}{month:02d}"] = urllib.parse.urljoin("https://www.federalreserve.gov", path)
    if not urls:
        raise ValueError("Fed calendar index has no months in requested window")
    return urls


def parse_dol_schedule(body, start, end):
    page = body.decode("utf-8-sig")
    if "Publication Schedule" not in page or "Thursday morning at 8:30am" not in page:
        raise ValueError("DOL weekly claims schedule changed")
    exceptions = set()
    for day in re.findall(r'<td[^>]*>(Wednesday|Friday|Tuesday|Monday), ([A-Za-z]+ \d{1,2}, \d{4})</td>', page):
        exceptions.add(datetime.strptime(day[1], "%B %d, %Y").date())
    day = start.date()
    events = []
    while day <= end.date():
        if day.weekday() == 3 and not any(abs((other - day).days) <= 2 for other in exceptions):
            when = datetime(day.year, day.month, day.day, 8, 30, tzinfo=ZoneInfo("America/New_York"))
            events.append(event("dol", "claims", "Đơn xin trợ cấp thất nghiệp Mỹ", "Unemployment Insurance Weekly Claims",
                                when, "medium", "labor", SOURCES["dol_schedule"]))
        if day in exceptions:
            when = datetime(day.year, day.month, day.day, 8, 30, tzinfo=ZoneInfo("America/New_York"))
            events.append(event("dol", "claims", "Đơn xin trợ cấp thất nghiệp Mỹ", "Unemployment Insurance Weekly Claims",
                                when, "medium", "labor", SOURCES["dol_schedule"]))
        day += timedelta(days=1)
    return events


def parse_dol_report(e, body, retrieved_at):
    from pypdf import PdfReader
    report = re.sub(r"\s+", " ", PdfReader(io.BytesIO(body)).pages[0].extract_text())
    local_day = datetime.fromisoformat(e["scheduled_at"].replace("Z", "+00:00")).astimezone(ZoneInfo("America/New_York")).date()
    if f"{local_day.strftime('%B')} {local_day.day}, {local_day.year}" not in report or "UNEMPLOYMENT INSURANCE WEEKLY CLAIMS" not in report:
        raise ValueError("DOL report release date does not match event")
    headline = report[report.index("SEASONALLY ADJUSTED DATA"):]
    average = re.search(r"The 4\s*-\s*week moving average", headline)
    if not average:
        raise ValueError("DOL initial claims section changed")
    headline = headline[:average.start()]
    match = re.search(r'week ending ([A-Za-z]+ \d{1,2}), the advance figure for seasonally adjusted initial claims was ([\d,]+)', headline)
    prior = re.search(r"previous week's (?:unrevised|revised) level of ([\d,]+)", headline)
    if not prior:
        prior = re.search(r"The previous week's level was revised (?:up|down) by [\d,]+ from [\d,]+ to ([\d,]+)", headline)
    if not match or not prior:
        raise ValueError("DOL initial claims headline changed")
    week_end = datetime.strptime(f"{match[1]}, {local_day.year}", "%B %d, %Y").date()
    if week_end > local_day:
        week_end = week_end.replace(year=local_day.year - 1)
    if (local_day - week_end).days not in {4, 5}:
        raise ValueError("DOL claims observation week mismatch")
    e.update(actual=int(match[2].replace(",", "")) / 1000,
             previous=int(prior[1].replace(",", "")) / 1000,
             unit="thousand_claims", reference_period=week_end.isoformat(),
             data_status="official_release", data_source_url=e["source_url"], data_vintage_at=retrieved_at)

def fetch_source(key, cache, now, max_age, url=None):
    url = url or SOURCES[key]
    file = cache / (key + ".json")
    old = json.loads(file.read_bytes()) if file.exists() else None
    if old and digest(base64.b64decode(old['body']) if old.get('body_encoding') == 'base64' else old['body'].encode()) != old['sha256']:
        raise ValueError('cached source checksum mismatch')
    if old and old.get("source_url") != url:
        old = None
    if old and (now - datetime.fromisoformat(old["checked_at"].replace("Z", "+00:00"))).total_seconds() < max_age:
        return old
    headers = {"User-Agent": "ECO-economic-calendar/1.0 (+https://eco.tnmp.cloud/)"}
    body = None
    if key == "bls_data":
        body = encode({"seriesid": [s[0] for s in SERIES.values()], "startyear": str(now.year - 1), "endyear": str(now.year)})
        headers["Content-Type"] = "application/json"
    elif old:
        if old.get("etag"):
            headers["If-None-Match"] = old["etag"]
        if old.get("last_modified"):
            headers["If-Modified-Since"] = old["last_modified"]
    request = urllib.request.Request(url, data=body, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=35) as response:
            if urllib.parse.urlparse(response.url).hostname != urllib.parse.urlparse(url).hostname:
                raise ValueError("unexpected official source redirect")
            raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ValueError("source body exceeded size limit")
            binary = key.startswith("dol_report_")
            old = {"source_url": url, "body": base64.b64encode(raw).decode() if binary else raw.decode("utf-8"),
                   "body_encoding": "base64" if binary else "utf-8", "sha256": digest(raw),
                   "retrieved_at": stamp(now), "etag": response.headers.get("ETag"),
                   "last_modified": response.headers.get("Last-Modified")}
    except urllib.error.HTTPError as exc:
        if exc.code != 304 or old is None:
            raise ValueError(f"{key}: HTTP {exc.code}") from None
    old["checked_at"] = stamp(now)
    write_json(file, old)
    return old

def backup_snapshot(folder, prefix="calendar"):
    """Bucket-limited SigV4 PUT/GET. No credentials, raw bodies or signed URLs in logs."""
    if prefix not in {"calendar", "macro-market"}:
        raise ValueError("invalid private snapshot prefix")
    account = os.environ.get("R2_ACCOUNT_ID", "")
    bucket = os.environ.get("R2_BUCKET", "eco-eth-private")
    access = os.environ.get("R2_ACCESS_KEY_ID", "")
    secret = os.environ.get("R2_SECRET_ACCESS_KEY", "")
    if not re.fullmatch(r"[a-f0-9]{32}", account) or bucket != "eco-eth-private" or not access or not secret:
        raise ValueError("missing bucket-limited R2 environment")
    host = f"{account}.r2.cloudflarestorage.com"
    def request(method, key, body=b""):
        now = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        day = now[:8]
        path = "/" + bucket + "/" + urllib.parse.quote(key, safe="/-_.~")
        sha = digest(body)
        canonical = f"{method}\n{path}\n\nhost:{host}\nx-amz-content-sha256:{sha}\nx-amz-date:{now}\n\nhost;x-amz-content-sha256;x-amz-date\n{sha}"
        scope = f"{day}/auto/s3/aws4_request"
        signing = ("AWS4" + secret).encode()
        for part in [day, "auto", "s3", "aws4_request"]:
            signing = hmac.new(signing, part.encode(), hashlib.sha256).digest()
        signature = hmac.new(signing, f"AWS4-HMAC-SHA256\n{now}\n{scope}\n{digest(canonical.encode())}".encode(), hashlib.sha256).hexdigest()
        headers = {"x-amz-date": now, "x-amz-content-sha256": sha,
                   "Authorization": f"AWS4-HMAC-SHA256 Credential={access}/{scope}, SignedHeaders=host;x-amz-content-sha256;x-amz-date, Signature={signature}"}
        try:
            with urllib.request.urlopen(urllib.request.Request(f"https://{host}{path}", data=body if method == "PUT" else None,
                                                               headers=headers, method=method), timeout=40) as r:
                return r.read()
        except urllib.error.HTTPError as exc:
            if method == "GET" and exc.code == 404:
                return None
            raise ValueError(f"R2 {method}: HTTP {exc.code}") from None
    results = []
    for file in sorted(folder.iterdir(), key=lambda p: (p.name == "manifest.json", p.name)):
        key = f"raw/{prefix}/{folder.name}/{file.name}"
        body = file.read_bytes()
        existing = request("GET", key)
        if existing is None:
            request("PUT", key, body)
        elif existing != body:
            raise ValueError("private snapshot collision")
        if request("GET", key) != body:
            raise ValueError("private snapshot readback mismatch")
        results.append({"object_key": key, "sha256": digest(body), "readback_verified": True})
    return results

def run_batch(root=ROOT, now=None):
    now = now or datetime.now(UTC)
    cache = root / "data/raw/calendar/cache"
    public = root / "public/data/calendar"
    sources = {}
    errors = []
    for key in SOURCES:
        try:
            # Once per UTC day for schedules; at most 3 API batches/day.
            age = 0 if key != "bls_data" and now.hour == 0 else (20 * 3600 if key != "bls_data" else 4 * 3600)
            sources[key] = fetch_source(key, cache, now, age)
        except Exception:
            errors.append(key)
    if errors:
        write_json(public / "status.json", {"schema_version": "1.0.0", "outcome": "source_error", "failed_sources": errors,
                                             "last_attempt_at": stamp(now), "last_good_retained": True})
        raise ValueError("official sources unavailable; retained last good calendar: " + ",".join(errors))
    try:
        start, end = now - timedelta(days=45), now + timedelta(days=180)
        month_urls = fed_month_urls(sources["fed_calendar"]["body"].encode(), start, end)
        for key, url in month_urls.items():
            sources[key] = fetch_source(key, cache, now, 0 if now.hour == 0 else 20 * 3600, url)
        events = parse_ics(sources["bls"]["body"].encode(), "bls") + parse_ics(sources["bea"]["body"].encode(), "bea") + parse_fed(sources["fed"]["body"].encode())
        for key, url in month_urls.items():
            ym = key.removeprefix("fed_month_")
            events.extend(parse_fed_month(sources[key]["body"].encode(), int(ym[:4]), int(ym[4:]), url))
        events.extend(parse_dol_schedule(sources["dol_schedule"]["body"].encode(), start, end))
        indicators = parse_indicators(sources["bls_data"]["body"].encode())
        attach_bls_results(events, indicators, now, sources["bls_data"]["retrieved_at"])
        bea_releases = parse_bea_schedule(sources["bea_schedule"]["body"].encode())
        for e in events:
            when = datetime.fromisoformat(e["scheduled_at"].replace("Z", "+00:00"))
            if e["provider"] != "bea" or e["kind"] not in {"pce", "gdp", "trade"} or not start <= when < now:
                continue
            url = bea_releases.get(e["source_title"])
            if not url:
                continue
            e["source_url"] = url
            key = "bea_report_" + re.sub(r"[^a-zA-Z0-9_]", "_", e["id"])
            sources[key] = fetch_source(key, cache, now, 4 * 3600, url)
            parse_bea_report(e, sources[key]["body"].encode(), sources[key]["retrieved_at"])
        for e in events:
            when = datetime.fromisoformat(e["scheduled_at"].replace("Z", "+00:00"))
            if e["provider"] != "dol" or not start <= when < now:
                continue
            local_day = when.astimezone(ZoneInfo("America/New_York")).date()
            url = f"https://oui.doleta.gov/press/{local_day.year}/{local_day.strftime('%m%d%y')}.pdf"
            e["source_url"] = url
            key = "dol_report_" + local_day.strftime("%Y%m%d")
            sources[key] = fetch_source(key, cache, now, 4 * 3600 if (now - when).days < 7 else 180 * 86400, url)
            parse_dol_report(e, base64.b64decode(sources[key]["body"]), sources[key]["retrieved_at"])
    except Exception:
        write_json(public / "status.json", {"schema_version": "1.0.0", "outcome": "validation_error", "last_attempt_at": stamp(now), "last_good_retained": True})
        raise
    events = sorted({e["id"]: e for e in events if start <= datetime.fromisoformat(e["scheduled_at"].replace("Z", "+00:00")) <= end}.values(), key=lambda e: (e["scheduled_at"], e["id"]))
    if len(events) < 30 or not all(any(e["provider"] == s for e in events) for s in ["bls", "bea", "fed", "dol"]):
        raise ValueError("calendar window lost official coverage")
    canonical = {"schema_version": "1.1.0", "calendar_version": VERSION, "scope": "US_major_macro",
                 "events": events, "indicators": indicators}
    content_hash = digest(encode(canonical))
    latest = public / "latest.json"
    old = json.loads(latest.read_bytes()) if latest.exists() else None
    if old and old.get("content_sha256") == content_hash:
        status = public / "status.json"
        prior_status = json.loads(status.read_bytes()) if status.exists() else {}
        if prior_status.get('outcome') != 'ok' or prior_status.get('last_success_at', '')[:10] != stamp(now)[:10]:
            write_json(status, {"schema_version": "1.0.0", "outcome": "ok", "last_success_at": stamp(now)})
        return {"outcome": "unchanged", "release_id": old["release_id"], "events": len(events)}
    snapshot = root / "data/raw/calendar" / (now.strftime("%Y%m%dT%H%M%S%fZ") + "-" + content_hash[:12])
    snapshot.mkdir(parents=True)
    files = {}
    for key, source in sources.items():
        name = key + ".json"
        write_json(snapshot / name, source)
        files[name] = digest((snapshot / name).read_bytes())
    write_json(snapshot / "canonical.json", canonical)
    files["canonical.json"] = content_hash
    write_json(snapshot / "manifest.json", {"status": "complete", "calendar_version": VERSION, "retrieved_at": stamp(now), "files": files})
    receipt = backup_snapshot(snapshot)  # Required before moving the public pointer.
    release_id = "calendar-" + content_hash[:20]
    release = public / "releases" / release_id
    data = {**canonical, "release_id": release_id, "generated_at": stamp(now),
            "sources": {key: {field: s.get(field) for field in ["source_url", "sha256", "retrieved_at", "checked_at", "last_modified"]} for key, s in sources.items()},
            "private_backup": {"verified": True, "snapshot_id": snapshot.name, "manifest_sha256": digest((snapshot / "manifest.json").read_bytes()), "objects": receipt},
            "revision": {"previous_release_id": old["release_id"], "reason": "expanded_official_coverage_and_period_matched_results"} if old else None}
    if (release / "calendar.json").exists():
        body = (release / "calendar.json").read_bytes()
    else:
        write_json(release / "calendar.json", data, immutable=True)
        body = (release / "calendar.json").read_bytes()
    write_json(latest, {"schema_version": "1.1.0", "release_id": release_id, "content_sha256": content_hash,
                        "url": f"/data/calendar/releases/{release_id}/calendar.json", "sha256": digest(body)})
    write_json(public / "status.json", {"schema_version": "1.0.0", "outcome": "ok", "last_success_at": stamp(now)})
    return {"outcome": "published", "release_id": release_id, "events": len(events), "indicators": len(indicators), "private_objects_verified": len(receipt)}

def run(root=ROOT, now=None):
    now = now or datetime.now(UTC)
    try:
        return run_batch(root, now)
    except Exception:
        status = root / 'public/data/calendar/status.json'
        existing = json.loads(status.read_bytes()) if status.exists() else {}
        if existing.get('last_attempt_at') != stamp(now):
            write_json(status, {'schema_version': '1.0.0', 'outcome': 'pipeline_error',
                                'last_attempt_at': stamp(now), 'last_good_retained': True})
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    print(json.dumps(run(), ensure_ascii=False))
