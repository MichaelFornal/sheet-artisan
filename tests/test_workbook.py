import tempfile
import unittest
import zipfile
from pathlib import Path

from openpyxl import load_workbook

from kit.workbook import build_workbook

SPEC = {
    "title": "Clinics in the Northeast",
    "key": ["id"],
    "columns": [
        {"name": "id", "type": "integer", "definition": "Row id", "source": "registry"},
        {"name": "name", "type": "text", "definition": "Clinic name", "source": "registry"},
        {"name": "beds", "type": "integer", "definition": "Licensed beds", "source": "registry"},
        {"name": "category", "type": "text", "definition": "Clinic type", "source": "derived",
         "derived": True, "ai": True},
        {"name": "source_url", "type": "url", "definition": "Where the row came from", "source": "all"},
        {"name": "fetched_at", "type": "datetime", "definition": "When it was fetched", "source": "all"},
    ],
    "sources": [
        {"name": "registry", "url": "https://registry.test/api", "method": "JSON API", "publish": "public",
         "license": "public record"},
        {"name": "portal", "url": "https://portal.test/hidden", "method": "internal JSON endpoint",
         "publish": "private", "license": "ToS silent"},
    ],
}

ROWS = [
    {"id": 1, "name": "Alpha", "beds": "1,234", "category": "urgent care",
     "source_url": "https://registry.test/1", "fetched_at": "2026-09-19T00:00:00Z", "_source": "registry"},
    {"id": 2, "name": "=cmd|' /C calc'!A0", "beds": 12, "category": "dental",
     "source_url": "https://portal.test/2", "fetched_at": "2026-09-19T01:00:00Z", "_source": "portal"},
    {"id": 3, "name": "Gam\x07ma", "beds": None, "category": None,
     "source_url": "https://registry.test/3", "fetched_at": "2026-09-19T02:00:00Z", "_source": "registry"},
]

START = """# Clinics in the Northeast
One row per licensed clinic.
## Headline
> Three clinics, most of them urgent care.
## How to use it
- [Top clinics by beds](#Top by beds)
- [The pipe](https://github.com/example/clinics)
Built **by hand**.
"""


def build(tier="private", rows=ROWS, **kw):
    out = Path(tempfile.mkdtemp()) / "t.xlsx"
    info = build_workbook(
        out, spec=SPEC, rows=rows, start_here_md=START, tier=tier,
        uses=[{"tab": "Top by beds", "title": "Top clinics by beds", "why": "Biggest first.",
               "rows": sorted(rows, key=lambda r: -(int(str(r["beds"]).replace(",", "")) if r["beds"] else 0)),
               "columns": ["name", "beds", "source_url"]}],
        summary=[{"title": "Rows by category", "header": ["category", "rows"],
                  "rows": [["urgent care", 1], ["dental", 1]], "chart": {"type": "bar", "title": "By category"}}],
        qa_rows=[("row count", "pass", "3 rows"), ("unique key", "fail", "1 dup")], **kw)
    return out, info


class WorkbookTests(unittest.TestCase):
    def test_tabs_in_order(self):
        out, info = build()
        wb = load_workbook(out)
        self.assertEqual(wb.sheetnames, ["Start Here", "Data", "Top by beds", "Summary", "Dictionary",
                                         "Sources & Method", "QA & Limits"])
        self.assertEqual(info["rows"], 3)

    def test_data_table_filters_freeze_and_links(self):
        out, _ = build()
        ws = load_workbook(out)["Data"]
        self.assertEqual(ws.freeze_panes, "A2")
        self.assertEqual([c.value for c in ws[1]], [c["name"] for c in SPEC["columns"]])
        table = list(ws.tables.values())[0]
        self.assertEqual(table.ref, "A1:F4")
        self.assertEqual(ws["E2"].hyperlink.target, "https://registry.test/1")

    def test_values_are_typed_and_sanitized(self):
        out, _ = build()
        ws = load_workbook(out)["Data"]
        self.assertEqual(ws["C2"].value, 1234)
        self.assertEqual(ws["B3"].value, "=cmd|' /C calc'!A0")
        self.assertEqual(ws["B3"].data_type, "s")  # text, never a formula
        self.assertEqual(ws["B4"].value, "Gamma")

    def test_start_here_links(self):
        out, _ = build()
        ws = load_workbook(out)["Start Here"]
        cells = {c.value: c for c in ws["A"] if c.value}
        self.assertTrue(cells["Clinics in the Northeast"].font.b)
        internal = cells["• Top clinics by beds"]
        self.assertEqual(internal.hyperlink.location, "'Top by beds'!A1")
        self.assertEqual(cells["• The pipe"].hyperlink.target, "https://github.com/example/clinics")
        self.assertIn("Built by hand.", cells)

    def test_use_tab(self):
        out, _ = build()
        ws = load_workbook(out)["Top by beds"]
        self.assertEqual(ws["A1"].value, "Top clinics by beds")
        self.assertEqual([c.value for c in ws[5]], ["name", "beds", "source_url"])
        self.assertEqual(ws["B6"].value, 1234)

    def test_dictionary_marks_ai_columns(self):
        out, _ = build()
        ws = load_workbook(out)["Dictionary"]
        self.assertEqual(ws.max_row, len(SPEC["columns"]) + 1)
        row = [c.value for c in ws[5]]
        self.assertEqual(row[0], "category")
        self.assertIn("AI", " ".join(str(v) for v in row))

    def test_sources_withheld_only_in_public_tier(self):
        out, _ = build(tier="public")
        ws = load_workbook(out)["Sources & Method"]
        portal = [c.value for c in ws[3]]
        self.assertEqual(portal[0], "portal")
        self.assertNotIn("https://portal.test/hidden", portal)
        self.assertIn("withheld", " ".join(str(v) for v in portal))
        out, _ = build(tier="private")
        portal = [c.value for c in load_workbook(out)["Sources & Method"][3]]
        self.assertIn("https://portal.test/hidden", portal)
        self.assertEqual(portal[3], 1)  # rows from that source

    def test_qa_tab(self):
        out, _ = build()
        ws = load_workbook(out)["QA & Limits"]
        self.assertEqual([c.value for c in ws[3]], ["unique key", "fail", "1 dup"])

    def test_summary_has_a_native_chart(self):
        out, _ = build()
        with zipfile.ZipFile(out) as z:
            self.assertTrue(any(n.startswith("xl/charts/chart") for n in z.namelist()))

    def test_empty_dataset_still_builds(self):
        out, info = build(rows=[])
        self.assertEqual(info["rows"], 0)
        self.assertEqual(load_workbook(out)["Data"].max_row, 1)

    def test_dangling_start_here_link_warns(self):
        out = Path(tempfile.mkdtemp()) / "t.xlsx"
        info = build_workbook(out, spec=SPEC, rows=ROWS, start_here_md="- [Gone](#No such tab)")
        self.assertIn("No such tab", " ".join(info["warnings"]))

    def test_long_and_duplicate_use_tab_names(self):
        out = Path(tempfile.mkdtemp()) / "t.xlsx"
        uses = [{"tab": "A very long use tab name that goes past thirty-one chars", "title": "x",
                 "why": "", "rows": ROWS}, {"tab": "Data", "title": "y", "why": "", "rows": ROWS}]
        build_workbook(out, spec=SPEC, rows=ROWS, start_here_md="# T", uses=uses)
        names = load_workbook(out).sheetnames
        self.assertEqual(len(names), len(set(names)))
        self.assertTrue(all(len(n) <= 31 for n in names))


if __name__ == "__main__":
    unittest.main()
