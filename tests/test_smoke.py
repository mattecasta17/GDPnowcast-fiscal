"""Smoke test — package imports and minimal function returns the expected value."""

from gdpnowcast import __version__
from gdpnowcast._smoke import smoke


def test_version_is_dev() -> None:
    assert __version__ == "0.2.0.dev0"


def test_smoke_returns_ok() -> None:
    assert smoke() == "ok"
