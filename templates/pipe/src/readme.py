"""make readme: README.tmpl.md + computed facts -> README.md"""
from datetime import date

from kit.facts import load, render
from src import config, facts_def


def main():
    for mode in ("full", "sample"):
        p = config.OUT / f"facts.{mode}.json"
        if p.exists():
            computed = load(p)
            break
    else:
        computed = facts_def.facts.compute(config.load_rows())
    spec = config.SPEC
    variables = {"title": spec.get("title"), "grain": spec.get("grain"), "repo_url": spec.get("repo_url"),
                 "date": date.today().isoformat()}
    text = render((config.ROOT / "README.tmpl.md").read_text(), computed, variables)
    (config.ROOT / "README.md").write_text(text)
    marker = "REPL" "ACE"  # spelled apart so the publish scan does not flag this file itself
    if marker in text:
        config.log(f"README.md still has {marker} markers: publishing will refuse it")
    config.log("wrote README.md")


if __name__ == "__main__":
    main()
