import numpy as np
import pytest

from afabm.config import set_path
from afabm.model import REGIMES, make_world, simulate
from afabm.policies import order_up_to, proportional, smooth
from afabm.shocks import ShockGenerator, haversine_km


def _bw(cfg, regime, seeds=8, key="bullwhip_retail"):
    return float(np.mean([simulate(make_world(cfg, np.random.default_rng(s)), cfg, regime).metrics[key] for s in range(seeds)]))


def test_world_is_deterministic_and_well_formed(cfg):
    a, b = make_world(cfg, np.random.default_rng(5)), make_world(cfg, np.random.default_rng(5))
    np.testing.assert_array_equal(a.demand, b.demand)
    assert a.demand.shape == (cfg["horizon_weeks"], 4) and (a.demand >= 0).all() and (a.supply > 0).all() and a.fc_eps.shape[0] == a.T


def test_common_random_numbers_across_shock_scales(cfg):
    a = make_world(set_path(cfg, "supply.shock_scale", 0.0), np.random.default_rng(5))
    b = make_world(set_path(cfg, "supply.shock_scale", 3.0), np.random.default_rng(5))
    np.testing.assert_array_equal(a.demand, b.demand)
    assert not np.allclose(a.supply, b.supply)


def test_shock_generator_is_spatially_correlated_and_left_skewed(cfg):
    lat, lon = cfg["farmers"]["lat"], cfg["farmers"]["lon"]
    x = ShockGenerator(haversine_km(lat, lon), **cfg["climate"]).sample(4000, np.random.default_rng(0))
    c, d = np.corrcoef(x.T), haversine_km(lat, lon)
    near = np.unravel_index(np.argsort(np.where(np.eye(6) == 1, 1e9, d), axis=None)[0], d.shape)
    far = np.unravel_index(np.argmax(d), d.shape)
    assert c[near] > c[far] and x.mean() < 0.02 and np.median(x) > x.mean()


@pytest.mark.parametrize("scale", [0.0, 3.0])
@pytest.mark.parametrize("regime", REGIMES)
def test_mass_balance_closes_and_bounds_hold(cfg, regime, scale):
    c = set_path(cfg, "supply.shock_scale", scale)
    w = make_world(c, np.random.default_rng(2))
    r = simulate(w, c, regime)
    assert r.metrics["mass_balance_err"] < 1e-9 and 0 <= r.metrics["fill_rate"] <= 1
    S = r.series
    assert (S["inv_retail"] >= -1e-9).all() and (S["inv_proc"] >= -1e-9).all() and (S["unmet"] >= -1e-9).all()
    assert (S["sales"] <= S["demand"] + 1e-9).all() and (S["delivered"] <= w.supply.sum(1) + 1e-9).all()


@pytest.mark.parametrize("regime", ["none", "pos", "vmi", "full"])
def test_deterministic_world_gives_steady_orders_and_full_service(cfg, regime):
    c = cfg
    for k, v in (("demand.noise_cv", 0.0), ("demand.seasonal_amp", 0.0), ("supply.seasonal_amp", 0.0), ("supply.noise_cv", 0.0), ("supply.shock_scale", 0.0)):
        c = set_path(c, k, v)
    r = simulate(make_world(c, np.random.default_rng(0)), c, regime)
    rel = lambda x: np.std(x[-30:]) / np.mean(x[-30:])  # noqa: E731
    assert r.metrics["fill_rate"] > 0.999 and rel(r.series["orders_retail"]) < 1e-3 and rel(r.series["orders_proc"]) < 1e-3


def test_bullwhip_exceeds_one_in_the_classic_setting(cfg):
    assert _bw(set_path(cfg, "supply.shock_scale", 0.0), "none") > 1.0


def test_more_reactive_forecasting_amplifies_orders(cfg):
    assert _bw(set_path(cfg, "policy.alpha_retailer", 0.8), "none") > _bw(set_path(cfg, "policy.alpha_retailer", 0.1), "none")


def test_gaming_inflates_orders_under_rationing_but_not_under_vmi(cfg):
    tight = set_path(set_path(cfg, "supply.shock_scale", 3.0), "farmers.capacity", [60, 55, 50, 45, 40, 40])
    g0, g1 = set_path(tight, "policy.gaming", 0.0), set_path(tight, "policy.gaming", 1.0)
    assert _bw(g1, "none") > _bw(g0, "none")
    w = make_world(tight, np.random.default_rng(3))
    assert simulate(w, g1, "vmi").metrics["bullwhip_retail"] == simulate(w, g0, "vmi").metrics["bullwhip_retail"]


def test_vmi_dampens_retail_orders_when_retailers_are_reactive(cfg):
    c = set_path(cfg, "policy.alpha_retailer", 0.6)
    assert _bw(c, "vmi") < _bw(c, "none")


def test_central_planner_serves_demand_without_amplifying_orders(cfg):
    m = simulate(make_world(cfg, np.random.default_rng(4)), cfg, "central").metrics
    assert m["fill_rate"] > 0.9 and m["bullwhip_retail"] < _bw(cfg, "none")


def test_helpers():
    q = np.array([30.0, 50.0])
    a = proportional(40.0, q)
    assert a.sum() == pytest.approx(40.0) and (a <= q).all() and proportional(500.0, q).sum() == pytest.approx(80.0) and proportional(5.0, np.zeros(2)).sum() == 0
    mu, var = smooth(np.array([10.0]), np.array([4.0]), np.array([14.0]), 0.3, 0.1)
    assert mu[0] == pytest.approx(0.3 * 14 + 0.7 * 10) and var[0] == pytest.approx(0.1 * 16 + 0.9 * 4)
    m, v, pos = np.array([10.0]), np.array([4.0]), np.array([12.0])
    assert order_up_to(m, v, pos, 2.0, 1.0, 1.0)[0] == pytest.approx(10 * 2 + np.sqrt(4 * 2) - 12)
    assert order_up_to(m, v, pos, 2.0, 1.0, 0.0)[0] == pytest.approx(10.0)
