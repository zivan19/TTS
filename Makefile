SHELL := /bin/bash
.PHONY: format lint test requirements-lock

format:
	black .
	ruff check --fix .

lint:
	ruff check .
	black --check .

# Run the unit tests.
test:
	pytest

# Export a deterministic dependency lock file for reproducible installs.
requirements-lock:
	python -m venv .venv-lock
	. .venv-lock/bin/activate && python -m pip install --upgrade pip && python -m pip install -r requirements.txt && python -m pip freeze --exclude-editable | sort > requirements-lock.txt
	rm -rf .venv-lock
