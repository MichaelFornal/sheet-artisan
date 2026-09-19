PY ?= python3
export PYTHONPATH := $(CURDIR)

.PHONY: help sample full sheet qa spot readme offline clean

help:  ## list targets
	@grep -E '^[a-z]+:.*## ' Makefile | sed 's/:.*## /	/'

sample:  ## small run (SAMPLE_N rows per source, default 25) all the way to a workbook
	MODE=sample $(PY) -m src.build
	MODE=sample $(PY) -m src.qa_run
	MODE=sample $(PY) -m src.sheet

full:  ## the whole crawl; safe to stop and re-run, it resumes from the cache
	MODE=full $(PY) -m src.build

sheet:  ## QA + workbook from the full crawl
	MODE=full $(PY) -m src.qa_run
	MODE=full $(PY) -m src.sheet

qa:  ## structural checks on the full crawl only
	MODE=full $(PY) -m src.qa_run

spot:  ## live spot-check: re-fetch 20 random rows and compare
	MODE=full $(PY) -m src.qa_run --spot

readme:  ## render README.md from README.tmpl.md with the computed facts
	$(PY) -m src.readme

offline:  ## rebuild everything from the cache, no network
	OFFLINE=1 MODE=full $(PY) -m src.build
	OFFLINE=1 MODE=full $(PY) -m src.qa_run
	OFFLINE=1 MODE=full $(PY) -m src.sheet

clean:  ## delete built rows and reports (keeps the fetch cache)
	rm -f data/rows.*.jsonl data/qa.*.json data/build.*.json data/progress.*.json
