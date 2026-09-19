"""make qa / make spot: structural checks (+ a live spot-check with --spot) -> data/qa.<mode>.json"""
import argparse
import json

from kit import qa
from src import config, sources


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spot", action="store_true", help="re-fetch random rows live and compare")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--strict", action="store_true", help="exit 1 when any check fails")
    args = ap.parse_args()

    rows = config.load_rows()
    spec = config.SPEC
    expected = spec.get("expected_rows") if config.MODE == "full" else None
    result = qa.run_checks(rows, spec, expected_rows=expected)
    path = config.DATA / f"qa.{config.MODE}.json"
    if args.spot:
        f = config.fetcher()
        result["spot_check"] = qa.spot_check(
            rows, lambda r: sources.by_name(r["_source"]).refetch(f, r),
            fields=spec.get("spot_check_fields") or [], n=args.n)
    elif path.exists():  # keep an earlier spot-check when only re-running the structural checks
        prev = json.loads(path.read_text()).get("spot_check")
        if prev:
            result["spot_check"] = prev
    path.write_text(json.dumps(result, indent=2, default=str))
    config.OUT.mkdir(parents=True, exist_ok=True)
    (config.OUT / "qa.md").write_text(qa.to_markdown(result, spec.get("limits", [])))
    for c in result["checks"]:
        config.log(f"qa {c['status']:>4}  {c['name']}: {c['detail']}")
    if result.get("spot_check"):
        s = result["spot_check"]
        config.log(f"qa {s['status']:>4}  spot-check: {s['match']}/{s['sampled']} match")
    if args.strict and not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
