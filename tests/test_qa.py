import unittest

from kit.qa import run_checks, spot_check, to_markdown

SPEC = {
    "key": ["id"],
    "columns": [
        {"name": "id", "type": "integer", "required": True},
        {"name": "name", "type": "text", "required": True},
        {"name": "employees", "type": "integer", "min": 0, "max": 100000},
        {"name": "tier", "type": "text", "enum": ["a", "b"]},
        {"name": "website", "type": "url"},
        {"name": "source_url", "type": "url", "required": True},
        {"name": "fetched_at", "type": "datetime", "required": True},
    ],
}


def row(i, **kw):
    base = {"id": i, "name": f"n{i}", "employees": 10, "tier": "a", "website": "https://x.test",
            "source_url": f"https://src.test/{i}", "fetched_at": "2026-09-19T00:00:00Z"}
    base.update(kw)
    return base


def status(result, name):
    return next(c["status"] for c in result["checks"] if c["name"] == name)


class QATests(unittest.TestCase):
    def test_clean_rows_pass(self):
        r = run_checks([row(i) for i in range(10)], SPEC, expected_rows=10)
        self.assertTrue(r["passed"], to_markdown(r))
        self.assertEqual(r["row_count"], 10)

    def test_empty_fails(self):
        self.assertFalse(run_checks([], SPEC)["passed"])

    def test_duplicate_keys_fail(self):
        r = run_checks([row(1), row(1), row(2)], SPEC)
        self.assertEqual(status(r, "unique key"), "fail")
        self.assertFalse(r["passed"])

    def test_missing_provenance_fails(self):
        r = run_checks([row(1), row(2, source_url=None)], SPEC)
        self.assertEqual(status(r, "provenance"), "fail")

    def test_required_null_fails_optional_null_warns(self):
        r = run_checks([row(1, name=None), row(2)], SPEC)
        self.assertEqual(status(r, "required columns"), "fail")
        r = run_checks([row(1, website=None), row(2, website=None), row(3)], SPEC)
        self.assertTrue(r["passed"])
        self.assertEqual(status(r, "null rates"), "warn")
        self.assertAlmostEqual(r["null_rates"]["website"], 2 / 3)

    def test_type_range_enum_url_warnings(self):
        rows = [row(1, employees="many"), row(2, employees=-5), row(3, tier="z"), row(4, website="ftp://x")]
        r = run_checks(rows, SPEC)
        self.assertEqual(status(r, "types"), "warn")
        self.assertEqual(status(r, "ranges"), "warn")
        self.assertEqual(status(r, "allowed values"), "warn")

    def test_short_of_expected_warns(self):
        r = run_checks([row(1)], SPEC, expected_rows=100)
        self.assertEqual(status(r, "row count"), "warn")

    def test_unknown_columns_warn(self):
        r = run_checks([row(1, surprise=1, _source="x")], SPEC)
        self.assertEqual(status(r, "unknown columns"), "warn")

    def test_spot_check(self):
        rows = [row(i) for i in range(10)]

        def refetch(r):
            if r["id"] == 3:
                return None
            if r["id"] == 4:
                raise RuntimeError("boom")
            if r["id"] == 5:
                return {"name": "renamed"}
            return {"name": r["name"]}
        s = spot_check(rows, refetch, fields=["name"], n=10)
        self.assertEqual((s["match"], s["changed"], s["gone"], s["error"]), (7, 1, 1, 1))
        self.assertEqual(s["status"], "warn")
        s = spot_check(rows[:3], lambda r: {"name": r["name"]}, fields=["name"])
        self.assertEqual(s["status"], "pass")


if __name__ == "__main__":
    unittest.main()
