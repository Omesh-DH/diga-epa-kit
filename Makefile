# Thin wrappers: every target is one script, so the same gate runs on
# Windows without make (see CLAUDE.md), in CI and in docker/validator.
PY ?= .venv/bin/python

.PHONY: setup spec test golden validate gate inventory

setup:
	python3 -m venv .venv
	$(PY) -m pip install -e ".[dev]"
	$(PY) scripts/fetch_spec.py

spec:
	$(PY) scripts/fetch_spec.py

test:
	$(PY) -m pytest -q

golden:
	UPDATE_GOLDEN=1 $(PY) -m pytest -q tests/golden
	git diff --stat tests/golden

validate: spec
	$(PY) scripts/validate.py --record

gate: test validate

inventory:
	$(PY) scripts/spec_inventory.py
