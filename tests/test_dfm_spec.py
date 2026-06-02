from gdpnowcast.dfm_spec import load_dfm_spec


def test_spec_model1_blocks_and_quarterly() -> None:
    spec = load_dfm_spec("Spec_US_new.xlsx")
    assert len(spec.series_id) == 28  # Model==1 rows (32 in file, 4 are Model==0)
    assert spec.blocks.shape[0] == len(spec.series_id)  # one block-row per kept series
    assert (spec.blocks[:, 0] == 1).all()  # all load on the global block
    assert set(spec.series_id[spec.frequency == "q"]) == {"GDPC1", "ULCNFB"}
    assert len(spec.units_transformed) == len(spec.series_id)  # display field present
