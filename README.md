# TTS

This repository is configured with automated testing and linting via GitHub Actions. The
primary development dependencies are pinned with upper bounds in `requirements.txt`, and the
exact, reproducible set used in CI is tracked in `requirements-lock.txt`.

## Development

Create a virtual environment, install dependencies, and run the quality checks locally:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
make lint
make test
```

### Exporting a lock file

To refresh `requirements-lock.txt` after dependency updates, run:

```bash
make requirements-lock
```

This target installs the dependencies and exports a deterministic lock file using `pip freeze`.
