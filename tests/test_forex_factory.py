import json
from datetime import date, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from eco import forex_factory as ff


START = date(2026, 11, 26)
END = date(2026, 11, 27)
MIDNIGHT = int(datetime(2026, 11, 26, tzinfo=ff.UTC).timestamp())


def page(**updates):
    event = {
        "id": 123, "currency": "USD", "name": "Example &amp; test",
        "impactName": "high", "dateline": MIDNIGHT + 1800, "timeMasked": False,
        "timeLabel": "12:30am", "date": "Nov 26, 2026", "hasDataValues": True,
        "leaked": False, "actual": "0", "forecast": "2.5%", "previous": "1%",
        "revision": "1.3%", "soloUrl": "/calendar/42-example",
    }
    event.update(updates)
    days = [
        {"date": "Thu <span>Nov 26</span>", "dateline": MIDNIGHT, "events": [event]},
        {"date": "Fri <span>Nov 27</span>", "dateline": None, "events": []},
    ]
    return (
        "<script>window.calendarSettings = {timezone_name: 'UTC'};\n"
        "window.calendarComponentStates[1] = {\ndays: "
        + json.dumps(days)
        + ', time: "ignored"};</script><tr data-event-id="123"></tr>'
    ).encode()


class ForexFactoryTests(TestCase):
    def test_units_zero_revision_utc_and_untimed(self):
        event, = ff.parse_calendar(page(), "utf-8", START, END)
        self.assertEqual(event["title"], "Example & test")
        self.assertEqual(event["actual"], "0")
        self.assertEqual(event["forecast"], "2.5%")
        self.assertEqual(event["previous"], "1.3%")
        self.assertEqual(event["previous_initial"], "1%")
        self.assertEqual(event["scheduled_at"], "2026-11-26T00:30:00Z")
        masked, = ff.parse_calendar(page(timeMasked=True, timeLabel="Tentative", leaked=True), "utf-8", START, END)
        self.assertIsNone(masked["scheduled_at"])
        self.assertIsNone(masked["actual"])
        self.assertEqual(masked["source_day"], "2026-11-26")
        self.assertEqual(masked["time_label"], "Tentative")

    def test_rejects_partial_range_and_mismatched_html(self):
        with self.assertRaisesRegex(ValueError, "date coverage"):
            ff.parse_calendar(page(), "utf-8", START, START)
        with self.assertRaisesRegex(ValueError, "visible calendar"):
            ff.parse_calendar(page().replace(b'event-id="123"', b'event-id="456"'), "utf-8", START, END)
        with self.assertRaisesRegex(ValueError, "outside its calendar day"):
            ff.parse_calendar(page(dateline=MIDNIGHT + 86400), "utf-8", START, END)

    def test_revision_unchanged_replay_and_failed_backup_leave_good_pointer(self):
        event, = ff.parse_calendar(page(), "utf-8", START, END)
        with TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / "public/data/forex-factory"
            with (
                patch.object(ff, "fetch_calendar", return_value=(b"raw html", "utf-8")),
                patch.object(ff, "parse_calendar", return_value=[event]) as parser,
                patch.object(ff, "backup_snapshot", return_value=[]) as backup,
            ):
                first = ff.run_batch(root, START)
                pointer_bytes = (output / "latest.json").read_bytes()
                pointer = json.loads(pointer_bytes)
                first_release = (root / ("public" + pointer["url"]))
                body = first_release.read_bytes()
                self.assertEqual(ff.digest(body), pointer["sha256"])
                self.assertEqual(ff.run_batch(root, START), first)
                self.assertEqual(backup.call_count, 1)

                parser.return_value = [{**event, "actual": "8.4%"}]
                backup.side_effect = ValueError("R2 PUT: HTTP 500")
                with self.assertRaisesRegex(ValueError, "r2_http_500"):
                    ff.run_batch(root, START)
                self.assertEqual((output / "latest.json").read_bytes(), pointer_bytes)
                self.assertEqual(json.loads((output / "status.json").read_bytes())["outcome"], "error")

                backup.side_effect = None
                second = ff.run_batch(root, START)
                self.assertNotEqual(first["release_id"], second["release_id"])
                self.assertEqual(first_release.read_bytes(), body)
                updated = json.loads((output / "releases" / second["release_id"] / "calendar.json").read_bytes())
                self.assertEqual(updated["revision_of"], first["release_id"])
