"""Pytest configuration for the repo root.

Puts the repository root on sys.path so the Phase-3 parity/golden tests can
`import Functions` (the A0-shimmed v1 pipeline) alongside the installed
src-layout `gdpnowcast` package. The v1 tree is not packaged/installed; it is
imported only by tests that pin the port against v1's exact behaviour.
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
