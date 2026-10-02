"""Frozen core-v0.1.0 mathematics. Calendar gaps never become observations."""

from bisect import bisect_left, insort
from collections import deque
from datetime import date, timedelta
import math

VERSION = "core-v0.1.0"
ORIGIN = date(2015, 8, 8)
COMPONENTS = ("E1", "E5", "E6", "E7")
WEIGHTS = {"E1": 1 / 6, "E5": 1 / 6, "E6": 1 / 6, "E7": 1 / 2}
EPSILON = 1e-12


def positive(value):
    if value is None:
        return None
    try:
        number = float(value)
    except (ValueError, TypeError):
        raise ValueError("invalid numeric input") from None
    if not math.isfinite(number) or number <= 0:
        raise ValueError("input must be finite and positive, or null")
    return number


def quantile(values, q):
    """Linear interpolation on an already sorted population."""
    position = (len(values) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


class Normalizer:
    def __init__(self):
        self.history = deque()
        self.sorted = []

    def compute(self, day, raw):
        boundary = day - timedelta(days=1460)
        while self.history and self.history[0][0] < boundary:
            _, old = self.history.popleft()
            self.sorted.pop(bisect_left(self.sorted, old))
        count = len(self.sorted)
        low = quantile(self.sorted, .05) if count >= 365 else None
        high = quantile(self.sorted, .95) if count >= 365 else None
        if raw is None:
            score, reason = None, "raw_unavailable"
        elif count < 365:
            score, reason = None, "normalizer_warmup"
        elif high - low <= EPSILON:
            score, reason = None, "degenerate_normalizer"
        else:
            score, reason = min(100., max(0., 100 * (raw - low) / (high - low))), None
        result = {"raw": raw, "score": score, "reason": reason,
                  "history_count": count, "lower": low, "upper": high}
        # Append only after evaluating t: today's value cannot set its own bounds.
        if raw is not None:
            self.history.append((day, raw))
            insort(self.sorted, raw)
        return result


def aggregate(scores, selected=COMPONENTS):
    selected = tuple(selected)
    if len(set(selected)) != len(selected) or any(k not in WEIGHTS for k in selected):
        raise ValueError("unknown or duplicate component")
    if not selected or any(scores.get(k) is None for k in selected):
        return None
    if any(not math.isfinite(scores[k]) or not 0 <= scores[k] <= 100 for k in selected):
        raise ValueError("component score out of bounds")
    return sum(scores[k] * WEIGHTS[k] for k in selected) / sum(WEIGHTS[k] for k in selected)


def compute(rows, end=None):
    by_date = {}
    for row in rows:
        day = date.fromisoformat(row["observation_date"])
        if day in by_date or row.get("asset") != "eth":
            raise ValueError("duplicate date or wrong asset")
        metrics = row["metrics"]
        if set(metrics) != {"PriceUSD", "CapMrktCurUSD", "CapMVRVCur", "SplyCur"}:
            raise ValueError("unexpected input schema")
        by_date[day] = {k: positive(v) for k, v in metrics.items()}
    if not by_date:
        raise ValueError("empty dataset")
    first, last = min(by_date), end or max(by_date)
    if last < max(by_date):
        raise ValueError("end precedes source observations")
    first_price = next((d for d in sorted(by_date) if by_date[d]["PriceUSD"] is not None), None)
    if first_price != ORIGIN:
        raise ValueError("price origin changed; a new methodology version is required")
    prices = deque(maxlen=730)
    normalizers = {k: Normalizer() for k in COMPONENTS}
    n = 0
    sx = sy = sxx = sxy = 0.
    cap_n, cap_mean, cap_m2 = 0, 0., 0.
    output = []
    day = first
    while day <= last:
        values = by_date.get(day, {})
        p, m, v = (values.get(k) for k in ("PriceUSD", "CapMrktCurUSD", "CapMVRVCur"))
        prices.append(p)

        def sma(window):
            series = list(prices)[-window:]
            return math.fsum(series) / window if len(series) == window and None not in series else None

        a111, a350, a730 = sma(111), sma(350), sma(730)
        raw = {"E1": math.log(a111 / (2 * a350)) if a111 and a350 else None,
               "E5": math.log(p / a730) if p and a730 else None, "E6": None, "E7": None}
        fit = None
        x = math.log(1 + (day - ORIGIN).days) if day >= ORIGIN else None
        denominator = n * sxx - sx * sx
        if p and n >= 730 and denominator > EPSILON:
            b = (n * sxy - sx * sy) / denominator
            a = (sy - b * sx) / n
            raw["E6"] = math.log(p) - a - b * x
            fit = {"intercept": a, "slope": b, "observations": n}
        sigma = math.sqrt(max(0., cap_m2 / cap_n)) if cap_n >= 365 else None
        realized = m / v if m and v else None
        if realized is not None and sigma and sigma > EPSILON:
            raw["E7"] = (m - realized) / sigma
        features = {k: normalizers[k].compute(day, raw[k]) for k in COMPONENTS}
        scores = {k: features[k]["score"] for k in COMPONENTS}
        score = aggregate(scores)
        output.append({"date": day.isoformat(), "price_usd": p, "score": score,
                       "coverage": sum(s is not None for s in scores.values()),
                       "components": features, "nupl_diagnostic": 1 - 1 / v if v else None,
                       "derived_realized_cap": realized, "e6_fit": fit,
                       "e7_sigma": sigma, "e7_past_count": cap_n,
                       "reason": None if score is not None else "incomplete_components",
                       "source_row_present": day in by_date})
        # Both OLS and population variance see today's observation only tomorrow.
        if p is not None:
            y = math.log(p)
            n += 1
            sx += x
            sy += y
            sxx += x * x
            sxy += x * y
        if m is not None:
            cap_n += 1
            delta = m - cap_mean
            cap_mean += delta / cap_n
            cap_m2 += delta * (m - cap_mean)
        day += timedelta(days=1)
    return output
