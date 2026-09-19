"""make sheet: rows + facts + QA + uses + Start Here -> the workbook (and, in a run, the email draft)."""
import json
from datetime import date

from kit import qa
from kit.facts import FactError, render, save
from kit.workbook import build_workbook
from src import config, facts_def, summary, uses


PENDING_LINK = "(link added at ship)"  # tools/check_run.py refuses to ship a sheet that still says this


def variables(pkg):
    spec = config.SPEC
    v = {"title": spec.get("title"), "grain": spec.get("grain"), "date": date.today().isoformat(),
         "repo_url": pkg.get("repo_url") or spec.get("repo_url") or PENDING_LINK}
    v.update({k: val for k, val in pkg.items() if isinstance(val, str) and val})
    return v


def main():
    rows = config.load_rows()
    spec, pkg = config.SPEC, config.package()
    config.OUT.mkdir(parents=True, exist_ok=True)
    computed = facts_def.facts.compute(rows)
    save(computed, config.OUT / f"facts.{config.MODE}.json")

    qa_path = config.DATA / f"qa.{config.MODE}.json"
    qa_result = json.loads(qa_path.read_text()) if qa_path.exists() else qa.run_checks(rows, spec)

    tmpl = config.PACKAGE / "start_here.md" if config.IN_RUN else config.ROOT / "templates" / "start_here.md"
    start_md = render(tmpl.read_text(), computed, variables(pkg))

    prefix = f"{pkg['workbook_prefix']}_" if pkg.get("workbook_prefix") else ""
    suffix = "_SAMPLE" if config.MODE == "sample" else ""
    path = config.OUT / f"{prefix}{spec.get('niche_slug') or 'dataset'}{suffix}_{date.today().isoformat()}.xlsx"
    info = build_workbook(
        path, spec=spec, rows=rows, start_here_md=start_md, uses=uses.uses(rows),
        summary=summary.tables(rows), qa_rows=qa.sheet_rows(qa_result, spec.get("limits", [])),
        # Private collection methods stay withheld even in the emailed copy unless the run opts in.
        tier="private" if pkg.get("show_private_methods") else "public")
    for w in info["warnings"]:
        config.log(f"WARNING {w}")
    config.log(f"workbook: {info['path']} ({info['rows']:,} rows, {info['size_bytes'] / 1e6:.1f} MB)")

    if config.IN_RUN and config.MODE == "full":
        for doc in ("email.md",):
            src = config.PACKAGE / doc
            if src.exists():
                try:
                    (config.OUT / doc).write_text(render(src.read_text(), computed, variables(pkg)))
                    config.log(f"rendered {doc} -> {config.OUT / doc}")
                except FactError as e:
                    config.log(f"{doc} not rendered yet: {e}")


if __name__ == "__main__":
    main()
