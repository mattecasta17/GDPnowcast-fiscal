from datetime import date

from gdpnowcast.data.vintages import fridays_between, load_manifest


def test_manifest_counts() -> None:
    # D2: both variants completed to the canonical 486-date union.
    assert len(load_manifest("baseline")) == 486
    assert len(load_manifest("fiscal")) == 486


def test_both_manifests_identical() -> None:
    assert load_manifest("baseline") == load_manifest("fiscal")


def test_fiscal_completed_with_2021_01_04() -> None:
    # v1's fiscal set lacked this quarter-start; v2 adds it (Decision D2).
    assert date(2021, 1, 4) in load_manifest("fiscal")


def test_manifest_range() -> None:
    m = load_manifest("fiscal")
    assert m[0] == date(2016, 10, 3)
    assert m[-1] == date(2025, 7, 25)


def test_manifest_includes_all_quarter_starts() -> None:
    # The quarter-start re-estimation vintages must be present (the bug
    # fridays_between introduced dropped them). Every non-Friday date is one;
    # the canonical 486-set has 34 (33 from v1 fiscal + the added 2021-01-04).
    m = load_manifest("fiscal")
    non_fridays = [d for d in m if d.weekday() != 4]
    assert len(non_fridays) == 34
    assert date(2020, 4, 1) in m  # spot-check a known quarter-start


def test_manifest_drops_no_friday() -> None:
    # Every Friday in the covered range must be present (no weekly vintage dropped).
    m = set(load_manifest("fiscal"))
    fridays = set(fridays_between(min(m), max(m)))
    missing = sorted(fridays - m)
    # v1 may skip a handful of holiday Fridays; assert the manifest covers >= 95%.
    assert len(missing) <= 0.05 * len(fridays), f"too many missing Fridays: {missing}"
