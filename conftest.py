"""Pytest configuration for the repo root.

Puts the repository root on sys.path so tests can import the `tools.*`
modules (e.g. tests/test_dashboard_data.py), which are not packaged with the
installed src-layout `gdpnowcast` package.
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
