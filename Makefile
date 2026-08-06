.PHONY: fix check test build release-check

fix:
	python scripts/release.py fix

check:
	python scripts/release.py check

test:
	python -m pytest

build:
	python scripts/release.py artifacts

release-check:
	python scripts/release.py all --native --require-clean
