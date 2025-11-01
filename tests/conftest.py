from __future__ import annotations

import sys
from pathlib import Path

# Ensure the project root (which contains the lightweight `tts` package used by
# the tests) is importable even when pytest changes the working directory.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
