from gdpnowcast.data.spec import SPEC_PATHS, load_spec


def test_baseline_has_32_series() -> None:
    assert len(load_spec(SPEC_PATHS["baseline"])) == 32


def test_fiscal_is_superset_of_baseline() -> None:
    base = {s.series_id for s in load_spec(SPEC_PATHS["baseline"])}
    fisc = {s.series_id for s in load_spec(SPEC_PATHS["fiscal"])}
    assert len(fisc) == 35
    assert base < fisc
    assert fisc - base == {"GCEC1", "MTSDS133FMS", "W875RX1"}


def test_quarterly_series_identified() -> None:
    q = {s.series_id for s in load_spec(SPEC_PATHS["fiscal"]) if s.frequency == "q"}
    assert q == {"GDPC1", "ULCNFB", "A261RX1Q020SBEA", "GCEC1"}


def test_spec_fields_typed() -> None:
    sp = next(s for s in load_spec(SPEC_PATHS["fiscal"]) if s.series_id == "GDPC1")
    assert sp.frequency == "q"
    assert sp.transform == "pca"
    assert isinstance(sp.model, int)
