.PHONY: all env data features model check test prototype
PY := .venv/bin/python -I
DATA ?= /Users/giocaballero/Downloads/00_Hackathon Materials/Data
# the original 10001_20000 zip repeats customers 1-10,000; the corrected upload is a folder
V2 ?= /Users/giocaballero/Downloads/2026 Avangrid Hackathon Data_10001_20000_v2
SOURCES = "$(DATA)/2026 Avangrid Hackathon Data_1_10000.zip" "$(V2)" "$(DATA)/2026 Avangrid Hackathon Data_20001_30000.zip" "$(DATA)/2026 Avangrid Hackathon Data_30001_35725.zip"

all: data features model check

env:
	uv venv -q .venv --python 3.12 && uv pip install -q --python .venv/bin/python -r requirements.txt

data:            ## zips -> data/processed/load.npy (about 20 s)
	$(PY) analysis/ingest.py $(SOURCES)

features:        ## load matrix + weather -> features.parquet
	$(PY) analysis/features.py

model:           ## classify, segment, size batteries -> facts/facts.json + outputs/
	$(PY) analysis/classify.py
	$(PY) analysis/segment.py
	$(PY) analysis/bess.py
	$(PY) analysis/report_data.py
	$(PY) analysis/report.py

check:           ## are we solving their problem, and is every number traced? (+ battery recompute and terms, about 140 s)
	$(PY) checks/check_all.py $(if $(DECK),--deck "$(DECK)")
	$(PY) checks/terms_check.py --selftest
	$(PY) checks/terms_check.py
	$(PY) checks/recompute_battery.py --selftest
	$(PY) checks/recompute_battery.py

test:            ## EWU prototype tests (config, house rules, then one file per milestone)
	$(PY) -m pytest -q tests/

prototype:       ## EWU prototype: check the config, then rebuild every EWU output and the demo page from data/processed
	$(PY) checks/config_check.py
	bin/ewu inventory
	$(PY) ewu/stress.py
	$(PY) ewu/attribution.py
	bin/ewu coldsnap
	$(PY) ewu/fitscore.py
	bin/ewu tophours
	bin/ewu sensitivity
	bin/ewu screen
	bin/ewu screen --managed
	bin/ewu screen --profile cautious
	bin/ewu network
	bin/ewu network --profile cautious
	bin/ewu plan
	bin/ewu robustness
	bin/ewu case
	bin/ewu demo --no-open
