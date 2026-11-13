.PHONY: all env data features model check
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
	$(PY) checks/compare.py
	$(PY) analysis/report.py

check:           ## are we solving their problem, and is every number traced?
	$(PY) checks/check_all.py $(if $(DECK),--deck "$(DECK)")
