import json

import pandas as pd

from afabm.config import load_config
from afabm.experiments import run_all, tune
from afabm.plotting import make_all
from afabm.provenance import export_parameters
from afabm.summary import summarize


def test_tuning_selects_the_cheapest_grid_point(cfg_copy, tmp_path):
    cfg_copy["experiments"]["tuning"].update(reps=1, covers=[1.0, 2.0], zs=[0.5, 1.28], thetas=[0.0, 0.5], regimes=["none", "full"])
    best = tune(cfg_copy, tmp_path)
    t = pd.read_csv(tmp_path / "tuning.csv")
    for r in ("none", "full"):
        row = t[t.regime == r].sort_values("cost_per_week").iloc[0]
        assert best[r]["cover"] == row.cover and best[r]["z"] == row.z
    assert best["full"]["theta"] in (0.0, 0.5) and best["none"]["theta"] is None and "central" in best


def test_end_to_end_run_figures_summary(tmp_path):
    out = tmp_path / "res"
    run_all("configs/quick.yaml", out)
    for f in ("regimes.csv", "shock_sweep.csv", "policy_map.csv", "gaming.csv", "forecast_noise.csv", "tuning.csv", "tuned_policies.json", "example_series.csv", "run_metadata.json"):
        assert (out / f).exists()
    assert len(make_all(out, tmp_path / "fig")) == 6
    s = summarize(out)
    assert "Price of decentralisation" in s and "E5" in s
    assert json.loads((out / "tuned_policies.json").read_text())["scale=1.0"]["central"]["cover"] is None


def test_parameter_table(tmp_path):
    df = export_parameters(load_config("configs/default.yaml"), tmp_path / "p.csv")
    assert list(df.columns) == ["key", "value", "status", "note"] and (df.status == "illustrative").all() and "costs.shortage" in set(df.key)
