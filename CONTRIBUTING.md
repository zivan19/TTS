# Contributing Guide

Thanks for your interest in improving TTS! This document walks you through the recommended development workflow so that your changes land smoothly.

## Prerequisites

- Python 3.10+
- `ffmpeg`
- Git

## Set up your environment

```bash
git clone https://github.com/your-user/TTS.git
cd TTS
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\\Scripts\\activate
pip install -e .[dev]
```

The `dev` extras install linters, test utilities, and documentation tooling. If the extras are unavailable, install the equivalent packages individually (e.g., `pytest`, `ruff`, `mkdocs`).

## Branching model

1. Create a branch off `main` named after the change you are making, e.g. `feature/improve-voice-picker`.
2. Keep your branch focused; send separate pull requests for unrelated fixes.

## Development workflow

1. **Sync** your fork and branch regularly:
   ```bash
   git fetch origin
   git rebase origin/main
   ```
2. **Implement** your feature or fix. Favor small, well-named functions and add docstrings for public interfaces.
3. **Add tests** alongside your code. Place unit tests under `tests/` and integration fixtures under `tests/integration/`.
4. **Run quality checks** before pushing:
   ```bash
   ruff check .
   pytest
   ```
5. **Update documentation** when behavior changes. Edit `README.md` for user-facing updates and create or adjust API docs as needed.
6. **Commit** with descriptive messages following Conventional Commits (e.g., `feat: add neural narrator`).

## Opening a pull request

1. Push your branch to your fork.
2. Open a PR against `main` with:
   - A concise summary of the change.
   - Testing evidence (commands + results).
   - Screenshots or audio samples if you changed output presentation.
3. Request a review from a maintainer.

## Code review tips

- Be responsive to feedback and follow up with clean commits.
- Prefer amending your branch over force-pushing after review unless requested.
- Mark conversations as resolved only after addressing them.

## Reporting issues

Before filing a bug, search existing issues. Include:

- Command(s) you ran
- Full log output with `--verbose`
- Platform, Python version, and whether you used GPU
- Steps to reproduce (with sample text if possible)

We appreciate your contributions and look forward to collaborating!
