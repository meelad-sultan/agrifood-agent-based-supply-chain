"""Experiments: regime comparison, shock sweep, ordering-policy map, shortage gaming, forecast quality, plus policy tuning (resumable)."""
from __future__ import annotations

import json
import platform
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from afabm import __version__
from afabm.config import load_config, set_path
from afabm.model import REGIMES, make_world, simulate

KEYS = ["fill_rate", "bullwhip_retail", "bullwhip_proc", "cost_per_week", "cost_hold", "cost_short", "cost_spoil", "cost_waste", "unmet_per_week",
        "stockout_week_share", "inv_retail", "inv_proc", "spoil_per_week", "waste_per_week", "mass_balance_err"]


def rng_for(seed, *keys):
    return np.random.default_rng(np.random.SeedSequence([int(seed), *[int(k) for k in keys]]))


def with_policy(cfg, regime, tuned):
    """Config with the tuned base-stock parameters of this regime applied (no-op if not tuned)."""
    t = (tuned or {}).get(regime)
    if not t:
        return cfg
    if regime == "central":
        return set_path(cfg, "policy.central.z", t["z"])
    for k in ("cover_retailer", "cover_processor"):
        cfg = set_path(cfg, f"policy.{k}", t["cover"])
    for k in ("z_retailer", "z_processor"):
        cfg = set_path(cfg, f"policy.{k}", t["z"])
    if regime == "full" and t.get("theta") is not None:
        cfg = set_path(cfg, "policy.supply_forecast.theta", t["theta"])
    return cfg


def _tune(cfg, regimes):
    """Grid-search the base-stock cover, safety factor (and, for `full`, the early-warning weight) on calibration worlds with separate seeds."""
    e = cfg["experiments"]["tuning"]
    rows, best = [], {}
    worlds = [make_world(cfg, rng_for(cfg["seed"], 99, e["seed_offset"] + i)) for i in range(e["reps"])]
    for regime in regimes:
        thetas = e.get("thetas", [None]) if regime == "full" else [None]
        grid = [(None, z, None) for z in e["zs"]] if regime == "central" else [(cv, z, th) for cv in e["covers"] for z in e["zs"] for th in thetas]
        for cover, z, th in grid:
            c = with_policy(cfg, regime, {regime: {"cover": cover, "z": z, "theta": th}})
            cost = np.mean([simulate(w, c, regime).metrics["cost_per_week"] for w in worlds])
            rows.append({"regime": regime, "cover": cover, "z": z, "theta": th, "cost_per_week": float(cost)})
        d = pd.DataFrame([r for r in rows if r["regime"] == regime]).sort_values("cost_per_week").iloc[0]
        best[regime] = {"cover": None if pd.isna(d.cover) else float(d.cover), "z": float(d.z), "theta": None if pd.isna(d.theta) else float(d.theta), "cost_per_week": float(d.cost_per_week)}
    return best, rows


def tune(cfg, out: Path, regimes=None) -> dict:
    regimes = regimes or list(cfg["experiments"]["tuning"]["regimes"]) + ["central"]
    best, rows = _tune(cfg, regimes)
    pd.DataFrame(rows).to_csv(out / "tuning.csv", index=False)
    (out / "tuned_policies.json").write_text(json.dumps(best, indent=2))
    return best


class Tuner:
    """Tunes every regime separately in every experimental condition (shock level, forecast noise); results are cached and persisted so an interrupted run can resume."""

    def __init__(self, cfg, out: Path | None = None):
        self.cfg, self.out, self.nested, self.rows = cfg, out, {}, []
        if out is not None and (out / "tuned_policies.json").exists() and (out / "tuning.csv").exists():
            self.nested = json.loads((out / "tuned_policies.json").read_text())
            self.rows = pd.read_csv(out / "tuning.csv").to_dict("records")

    def get(self, cond_cfg, key, regimes=None):
        regimes = list(regimes or list(self.cfg["experiments"]["tuning"]["regimes"]) + ["central"])
        have = self.nested.get(key, {})
        missing = [r for r in regimes if r not in have]
        if missing:
            best, rows = _tune(cond_cfg, missing)
            self.nested.setdefault(key, {}).update(best)
            self.rows += [{"condition": key, **r} for r in rows]
            print(f"  tuned [{key}]: " + ", ".join(f"{k}=({v['cover']}, {v['z']}, {v['theta']})" for k, v in best.items()), flush=True)
            self.save()
        return {r: self.nested[key][r] for r in regimes}

    def save(self):
        if self.out is not None:
            pd.DataFrame(self.rows).to_csv(self.out / "tuning.csv", index=False)
            (self.out / "tuned_policies.json").write_text(json.dumps(self.nested, indent=2))


def _run(cfg, exp_id, reps, regimes, tuned, extra=None, label="run"):
    rows, t0 = [], time.perf_counter()
    for rep in range(reps):
        world = make_world(cfg, rng_for(cfg["seed"], exp_id, rep))
        for regime in regimes:
            for variant, tun in (("tuned", tuned), ("default", None)) if extra is None else (("tuned", tuned),):
                m = simulate(world, with_policy(cfg, regime, tun), regime).metrics
                rows.append({"rep": rep, "regime": regime, "variant": variant, **{k: m[k] for k in KEYS}})
    print(f"  [{label}] {reps} reps done ({time.perf_counter() - t0:.0f}s)", flush=True)
    return rows


def run_regimes(cfg, out, tuner):
    e = cfg["experiments"]["regimes"]
    c = set_path(cfg, "supply.shock_scale", e["shock_scale"])
    tuned = tuner.get(c, f"scale={float(e['shock_scale'])}")
    pd.DataFrame(_run(c, 1, e["reps"], cfg["regimes"], tuned, label="regimes")).to_csv(out / "regimes.csv", index=False)
    rows = []  # one recorded example run per regime for the time-series figure
    world = make_world(c, rng_for(cfg["seed"], 1, 0))
    for regime in ("none", "vmi", "central"):
        S = simulate(world, with_policy(c, regime, tuned), regime).series
        rows += [{"regime": regime, "week": t, **{k: float(S[k][t]) for k in ("demand", "orders_retail", "orders_proc", "inv_retail", "inv_proc", "unmet")}} for t in range(world.T)]
    pd.DataFrame(rows).to_csv(out / "example_series.csv", index=False)


def run_shock_sweep(cfg, out, tuner):
    e, rows = cfg["experiments"]["shock_sweep"], []
    for sc in e["scales"]:
        c = set_path(cfg, "supply.shock_scale", sc)
        for r in _run(c, 2, e["reps"], cfg["regimes"], tuner.get(c, f"scale={float(sc)}"), extra=1, label=f"shock {sc}"):
            rows.append({"shock_scale": sc, **r})
    pd.DataFrame(rows).to_csv(out / "shock_sweep.csv", index=False)


def run_policy_map(cfg, out, tuner):
    e, rows = cfg["experiments"]["policy_map"], []
    tuned = tuner.get(cfg, f"scale={float(cfg['supply']['shock_scale'])}")
    for al in e["alphas"]:
        for be in e["betas"]:
            c = set_path(set_path(cfg, "policy.alpha_retailer", al), "policy.beta", be)
            for r in _run(c, 3, e["reps"], e["regimes"], tuned, extra=1, label=f"map a={al} b={be}"):
                rows.append({"alpha_retailer": al, "beta": be, **r})
    pd.DataFrame(rows).to_csv(out / "policy_map.csv", index=False)


def run_gaming(cfg, out, tuner):
    e, rows = cfg["experiments"]["gaming"], []
    base = set_path(cfg, "supply.shock_scale", e["shock_scale"])
    tuned = tuner.get(base, f"scale={float(e['shock_scale'])}")
    for gv in e["values"]:
        for r in _run(set_path(base, "policy.gaming", gv), 4, e["reps"], e["regimes"], tuned, extra=1, label=f"gaming {gv}"):
            rows.append({"gaming": gv, **r})
    pd.DataFrame(rows).to_csv(out / "gaming.csv", index=False)


def run_forecast_noise(cfg, out, tuner):
    e, rows = cfg["experiments"]["forecast_noise"], []
    base = set_path(cfg, "supply.shock_scale", e["shock_scale"])
    for nv in e["values"]:
        c = set_path(base, "policy.supply_forecast.noise_cv", nv)
        tuned = tuner.get(c, f"scale={float(e['shock_scale'])}|noise={float(nv)}", ["full", "central"])
        for r in _run(c, 5, e["reps"], e["regimes"], tuned, extra=1, label=f"forecast noise {nv}"):
            rows.append({"forecast_noise": nv, **r})
    pd.DataFrame(rows).to_csv(out / "forecast_noise.csv", index=False)


STEPS = {"regimes": run_regimes, "shock_sweep": run_shock_sweep, "policy_map": run_policy_map, "gaming": run_gaming, "forecast_noise": run_forecast_noise}


def run_all(config, out_dir, only=None):
    cfg = load_config(config)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    t0, timings = time.perf_counter(), {}
    print(f"afabm {__version__} | config {config} | out {out}", flush=True)
    tuner = Tuner(cfg, out)
    if only is None:  # tune every condition up front (cached on disk), so the tuning table is complete even when finished steps are skipped
        s0 = float(cfg["experiments"]["regimes"]["shock_scale"])
        conds = [(set_path(cfg, "supply.shock_scale", s0), f"scale={s0}")] + [(set_path(cfg, "supply.shock_scale", sc), f"scale={float(sc)}") for sc in cfg["experiments"]["shock_sweep"]["scales"]]
        for c, k in conds:
            tuner.get(c, k)
    outputs = {"regimes": "regimes.csv", "shock_sweep": "shock_sweep.csv", "policy_map": "policy_map.csv", "gaming": "gaming.csv", "forecast_noise": "forecast_noise.csv"}
    for name in only or STEPS:
        if only is None and (out / outputs[name]).exists():
            print(f"[{name}] skipped (output exists; delete {outputs[name]} to recompute)", flush=True)
            continue
        t1 = time.perf_counter()
        print(f"[{name}] start", flush=True)
        STEPS[name](cfg, out, tuner)
        timings[name] = round(time.perf_counter() - t1, 1)
    import scipy
    meta = {"afabm_version": __version__, "config_path": str(config), "config": cfg, "timings_s": timings, "total_s": round(time.perf_counter() - t0, 1),
            "python": sys.version.split()[0], "platform": platform.platform(), "packages": {"numpy": np.__version__, "scipy": scipy.__version__, "pandas": pd.__version__}}
    (out / "run_metadata.json").write_text(json.dumps(meta, indent=2, default=str))
    print(f"all done in {meta['total_s']} s -> {out}", flush=True)


__all__ = ["run_all", "tune", "Tuner", "with_policy", "rng_for", "REGIMES"]
