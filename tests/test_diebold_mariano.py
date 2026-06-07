"""Tests for the Diebold-Mariano + Harvey-Leybourne-Newbold module."""

from __future__ import annotations

import numpy as np
import pytest
from scipy import stats

from gdpnowcast.diebold_mariano import diebold_mariano


def test_identical_losses_are_not_significant() -> None:
    loss = [1.0, 2.0, 0.5, 3.0, 1.5]
    r = diebold_mariano(loss, loss)
    assert r.dm_stat == 0.0
    assert r.p_value == 1.0
    assert r.mean_loss_diff == 0.0
    assert r.df == 4 and r.n == 5


def test_model_a_clearly_better_is_significant_and_negative() -> None:
    # d_t = loss_a - loss_b ~= -0.5 with tiny alternating variation => A much lower loss.
    n = 20
    loss_b = [1.0] * n
    loss_a = [1.0 + (-0.5 + 0.05 * (-1) ** t) for t in range(n)]
    r = diebold_mariano(loss_a, loss_b)
    assert r.mean_loss_diff < 0  # A has the lower loss
    assert r.dm_stat < 0
    assert r.p_value < 0.01


def test_symmetry_swapping_models_flips_sign() -> None:
    loss_a = [1.0, 2.0, 1.5, 3.0, 2.5, 1.0, 2.0, 1.5]
    loss_b = [1.5, 2.5, 1.0, 3.5, 2.0, 1.5, 2.5, 2.0]
    ab = diebold_mariano(loss_a, loss_b)
    ba = diebold_mariano(loss_b, loss_a)
    assert ab.dm_stat == pytest.approx(-ba.dm_stat)
    assert ab.p_value == pytest.approx(ba.p_value)
    assert ab.mean_loss_diff == pytest.approx(-ba.mean_loss_diff)


def test_matches_independent_derivation_h1() -> None:
    loss_a = [1.0, 2.0, 1.5, 3.0, 2.5, 1.0, 2.0, 1.5]
    loss_b = [1.5, 2.5, 1.0, 3.5, 2.0, 1.5, 2.5, 2.0]
    r = diebold_mariano(loss_a, loss_b, horizon=1)

    # Independent re-derivation (h=1: long-run variance = biased sample variance).
    d = np.array(loss_a) - np.array(loss_b)
    n = len(d)
    dbar = d.mean()
    gamma0 = np.mean((d - dbar) ** 2)
    dm = dbar / np.sqrt(gamma0 / n)
    factor = np.sqrt((n - 1) / n)  # h=1 HLN factor
    expected_stat = dm * factor
    expected_p = 2.0 * stats.t.sf(abs(expected_stat), n - 1)

    assert r.dm_stat == pytest.approx(expected_stat)
    assert r.p_value == pytest.approx(expected_p)
    assert r.df == n - 1


def test_horizon_gt_1_uses_autocovariances_and_runs() -> None:
    rng = np.random.default_rng(0)
    loss_a = rng.normal(size=30).tolist()
    loss_b = rng.normal(size=30).tolist()
    r = diebold_mariano(loss_a, loss_b, horizon=4)
    assert r.horizon == 4
    assert r.df == 29
    assert np.isfinite(r.dm_stat) and 0.0 <= r.p_value <= 1.0


def test_validation_errors() -> None:
    with pytest.raises(ValueError):
        diebold_mariano([1.0, 2.0], [1.0, 2.0, 3.0])  # shape mismatch
    with pytest.raises(ValueError):
        diebold_mariano([1.0], [2.0])  # n < 2
    with pytest.raises(ValueError):
        diebold_mariano([1.0, 2.0], [2.0, 3.0], horizon=0)  # bad horizon
