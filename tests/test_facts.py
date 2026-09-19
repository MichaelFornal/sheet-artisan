import json
import tempfile
import unittest
from pathlib import Path

from kit.facts import FactError, Facts, bare_numbers, load, render, save

ROWS = [{"city": "Boston", "n": 3}, {"city": "Boston", "n": 5}, {"city": "Austin", "n": None}]


def registry():
    facts = Facts()

    @facts.fact("row_count", "Rows in the dataset", fmt="int")
    def row_count(rows):
        return len(rows) * 1000

    @facts.fact("boston_share", "Share of rows in Boston", fmt="pct")
    def boston_share(rows):
        return sum(r["city"] == "Boston" for r in rows) / len(rows)

    @facts.fact("top_city", "Most common city", fmt="text")
    def top_city(rows):
        return "Boston"

    @facts.fact("avg_n", "Mean of n", fmt="float1")
    def avg_n(rows):
        vals = [r["n"] for r in rows if r["n"] is not None]
        return sum(vals) / len(vals)

    @facts.fact("revenue", "Revenue", fmt="money")
    def revenue(rows):
        return 1234567
    return facts


class FactsTests(unittest.TestCase):
    def test_compute_formats(self):
        f = registry().compute(ROWS)
        self.assertEqual(f["row_count"]["display"], "3,000")
        self.assertEqual(f["row_count"]["value"], 3000)
        self.assertEqual(f["boston_share"]["display"], "67%")
        self.assertEqual(f["top_city"]["display"], "Boston")
        self.assertEqual(f["avg_n"]["display"], "4.0")
        self.assertEqual(f["revenue"]["display"], "$1,234,567")
        self.assertEqual(f["row_count"]["desc"], "Rows in the dataset")

    def test_duplicate_key_rejected(self):
        facts = Facts()
        facts.fact("a", "x")(lambda rows: 1)
        with self.assertRaises(FactError):
            facts.fact("a", "y")(lambda rows: 2)

    def test_save_load_roundtrip(self):
        p = Path(tempfile.mkdtemp()) / "facts.json"
        save(registry().compute(ROWS), p)
        self.assertEqual(load(p)["row_count"]["display"], "3,000")
        self.assertIn("computed_at", json.loads(p.read_text())["_meta"])

    def test_render(self):
        f = registry().compute(ROWS)
        out = render("We found {{fact:row_count}} rows; {{fact:boston_share}} in {{fact:top_city}}. "
                     "Open {{lit:24/7}}. Hi {{var:company}}.", f, {"company": "Acme"})
        self.assertEqual(out, "We found 3,000 rows; 67% in Boston. Open 24/7. Hi Acme.")

    def test_render_unknown_keys_raise_listing_all(self):
        with self.assertRaises(FactError) as cm:
            render("{{fact:nope}} {{fact:also_nope}} {{var:who}}", {}, {})
        msg = str(cm.exception)
        self.assertIn("nope", msg)
        self.assertIn("also_nope", msg)
        self.assertIn("who", msg)

    def test_bare_numbers_flags_unbacked_digits(self):
        hits = bare_numbers("We scraped 4,000 sites and {{fact:row_count}} rows.\n10x faster.")
        self.assertEqual([h[0] for h in hits], [1, 2])
        self.assertIn("4,000", hits[0][1])

    def test_bare_numbers_allows_the_harmless_cases(self):
        text = "\n".join([
            "# Title",
            "1. First use",
            "2) Second use",
            "Data as of 2026-09-19 and 2026-09-19T10:00:00Z.",
            "See https://example.com/page/42 and [the repo](https://github.com/x/y2).",
            "Run `make sample N=25` then:",
            "```",
            "python3 -m src.build --limit 500",
            "```",
            "Works for B2B teams, Q3 plans, S3 buckets, GPT4.",
            "{{lit:24/7}} and {{fact:row_count}} and {{var:repo_url}}",
            "<!-- 99 bottles -->",
        ])
        self.assertEqual(bare_numbers(text), [])

    def test_bare_numbers_catches_leading_digit_tokens(self):
        self.assertEqual(len(bare_numbers("10k rows")), 1)
        self.assertEqual(len(bare_numbers("a 3D map")), 1)
        self.assertEqual(len(bare_numbers("costs $5")), 1)


if __name__ == "__main__":
    unittest.main()
