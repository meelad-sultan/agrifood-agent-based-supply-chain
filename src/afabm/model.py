"""World generation and the weekly agent-based simulation.

Chain: farmers -> processors -> retailers -> consumers; one raw unit becomes one product unit. Raw milk is perishable (shipped the week
it is produced); product stock spoils at a small weekly rate at processors and a larger one at retailers; unmet demand is lost.

Weekly sequence: (1) retail shipments dispatched last week arrive; (2) consumer demand is served from stock and the rest is lost;
(3) retail stock spoils; (4) forecasts are updated and orders are formed; (5) processors order raw milk; (6) farmers deliver
(rationing pro rata if production is short); (7) processors ship to retailers (rationing pro rata); (8) processor stock spoils; costs accrue.

Information regimes (a ladder; each adds one thing to the previous one):
  none    retailers order from their own demand history; processors forecast from the orders they receive (the classic bullwhip setting)
  pos     processors also see consumer sales (point-of-sale data) and forecast from them; retailers still order themselves
  vmi     processors manage retailer replenishment (vendor-managed inventory) from pooled sales data; retailers place no orders
  full    vmi plus a shared early warning of coming supply shortfalls (a climate forecast with configurable error)
  central one planner with full information and flexible shipping solves a rolling-horizon linear programme (coordination benchmark)
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from afabm.policies import central_plan, order_up_to, proportional, smooth
from afabm.shocks import ShockGenerator, haversine_km

REGIMES = ["none", "pos", "vmi", "full", "central"]


@dataclass
class World:
    demand: np.ndarray  # (T, R) realised consumer demand
    mean_demand: np.ndarray  # (T, R) true seasonal mean
    sigma_total: np.ndarray  # (T,) true standard deviation of total demand
    supply: np.ndarray  # (T, F) realised production
    supply_expect: np.ndarray  # (T,) expected total production (shock profile, no weekly noise)
    fc_eps: np.ndarray  # (T, H) standard-normal draws used for supply-forecast error
    T: int


@dataclass
class Result:
    metrics: dict
    series: dict


def _profile(w, window, ramp):
    return np.clip(np.minimum((w - window[0] + 1) / ramp, (window[1] - w + 1) / ramp), 0.0, 1.0)


def _ar1(T, n, phi, rng):
    e, innov = np.zeros((T, n)), rng.standard_normal((T, n)) * np.sqrt(1 - phi**2)
    e[0] = rng.standard_normal(n)
    for t in range(1, T):
        e[t] = phi * e[t - 1] + innov[t]
    return e


def make_world(cfg: dict, rng: np.random.Generator) -> World:
    T, d, s = int(cfg["horizon_weeks"]), cfg["demand"], cfg["supply"]
    base, cap = np.array(cfg["retailers"]["base_demand"], float), np.array(cfg["farmers"]["capacity"], float)
    t = np.arange(T)
    mean = base[None, :] * (1 + d["seasonal_amp"] * np.sin(2 * np.pi * t / 52))[:, None]
    cs = d["common_share"]
    eps = np.sqrt(cs) * _ar1(T, 1, d["ar_phi"], rng) + np.sqrt(1 - cs) * _ar1(T, len(base), d["ar_phi"], rng)
    demand = np.maximum(0.0, mean * (1 + d["noise_cv"] * eps))
    tot, sq = mean.sum(1), (mean**2).sum(1)
    sigma_total = d["noise_cv"] * np.sqrt(sq + cs * (tot**2 - sq))
    gen = ShockGenerator(haversine_km(cfg["farmers"]["lat"], cfg["farmers"]["lon"]), **cfg["climate"])
    xi = gen.sample(T // 52 + 2, rng) * s["shock_scale"]
    mult = np.clip(1 + xi[t // 52] * _profile(t % 52, s["shock_window_weeks"], s["ramp_weeks"])[:, None], 0.2, None)
    season = 1 + s["seasonal_amp"] * np.sin(2 * np.pi * (t - 13) / 52)
    expect = cap[None, :] * season[:, None] * mult
    supply = expect * np.clip(1 + s["noise_cv"] * rng.standard_normal(expect.shape), 0.5, None)
    H = max(int(cfg["policy"]["supply_forecast"]["horizon_weeks"]), int(cfg["policy"]["central"]["horizon_weeks"]))
    return World(demand, mean, sigma_total, supply, expect.sum(1), rng.standard_normal((T, H)), T)


def simulate(world: World, cfg: dict, regime: str) -> Result:
    if regime not in REGIMES:
        raise ValueError(f"unknown regime {regime}")
    P, C, sp, T = cfg["policy"], cfg["costs"], cfg["spoilage"], world.T
    kp = np.array(cfg["processors"]["capacity"], float)
    nP, R = len(kp), world.demand.shape[1]
    home = np.array(cfg["retailers"]["home_processor"], int)
    base = np.array(cfg["retailers"]["base_demand"], float)
    grp = np.array([base[home == p].sum() for p in range(nP)])
    share = base / grp[home]
    sf = P["supply_forecast"]
    a, a_r, a_s, beta, g = P["alpha"], P["alpha_retailer"], P["alpha_sigma"], P["beta"], P["gaming"]
    cv = cfg["demand"]["noise_cv"]
    mu_r = world.mean_demand[0].copy()
    var_r = (cv * mu_r) ** 2
    mu_o = np.bincount(home, weights=mu_r, minlength=nP)
    var_o = (cv * mu_o) ** 2
    IR, IP = mu_r * P["cover_retailer"], mu_o * P["cover_processor"]
    arr, prev_fill = np.zeros(R), np.ones(R)
    initial_stock = float(IR.sum() + IP.sum())
    keys = ["demand", "orders_retail", "orders_proc", "sales", "unmet", "inv_retail", "inv_proc", "delivered", "waste", "spoil", "cost_hold", "cost_short", "cost_spoil", "cost_waste"]
    S = {k: np.zeros(T) for k in keys}
    for t in range(T):
        IR = IR + arr
        arr = np.zeros(R)
        d = world.demand[t]
        sales = np.minimum(IR, d)
        IR = IR - sales
        sp_r = sp["retailer"] * IR
        IR = IR - sp_r
        mu_r, var_r = smooth(mu_r, var_r, d, a_r, a_s)
        Dp = np.bincount(home, weights=d, minlength=nP)
        if regime == "central":
            x_tot, y_tot = central_plan(float(IP.sum()), float(IR.sum()), t, world, cfg)
            x_tot = min(x_tot, float(world.supply[t].sum()))
            deliv = x_tot * kp / kp.sum()
            IP = IP + deliv
            take = y_tot * IP / max(float(IP.sum()), 1e-12)
            IP = IP - take
            nxt = min(t + 1, T - 1)
            tgt = base / base.sum() * (world.mean_demand[nxt].sum() + P["central"]["z"] * world.sigma_total[nxt])
            need = np.maximum(0.0, tgt - IR)
            ship = proportional(float(take.sum()), need) if need.sum() > 1e-12 else 0.0 * need
            ship = ship + (take.sum() - ship.sum()) * base / base.sum()
            arr, q, O = ship, ship, np.array([x_tot])
            waste = max(0.0, float(world.supply[t].sum()) - float(deliv.sum()))
        else:
            if regime in ("none", "pos"):
                q = order_up_to(mu_r, var_r, IR, P["cover_retailer"], P["z_retailer"], beta) * (1 + g * (1 - prev_fill))
                x_sig = np.bincount(home, weights=q, minlength=nP) if regime == "none" else Dp
            else:
                x_sig = Dp
            mu_o, var_o = smooth(mu_o, var_o, x_sig, a, a_s)
            if regime in ("vmi", "full"):
                q = order_up_to(mu_o[home] * share, var_o[home] * share**2, IR, P["cover_retailer"], P["z_retailer"], beta)
            tgt = mu_o * P["cover_processor"] + P["z_processor"] * np.sqrt(var_o * P["cover_processor"])
            if regime == "full":
                H = int(sf["horizon_weeks"])
                exp_sup = world.supply_expect[np.minimum(t + 1 + np.arange(H), T - 1)] * (1 + sf["noise_cv"] * world.fc_eps[t, :H])
                dem = float(mu_o.sum())
                extra = min(sf["theta"] * float(np.maximum(0.0, dem - exp_sup).sum()), sf["max_build_weeks"] * dem)
                tgt = tgt + extra * mu_o / max(dem, 1e-12)
            O = np.clip((1 - beta) * mu_o + beta * (tgt - IP), 0.0, kp)
            tot_a, tot_o = float(world.supply[t].sum()), float(O.sum())
            deliv = O * (min(1.0, tot_a / tot_o) if tot_o > 1e-12 else 1.0)
            waste = max(0.0, tot_a - float(deliv.sum()))
            IP = IP + deliv
            ship = np.zeros(R)
            for p in range(nP):
                m = home == p
                ship[m] = proportional(float(IP[p]), q[m])
                IP[p] -= ship[m].sum()
            arr = ship
            prev_fill = np.where(q > 1e-9, ship / np.maximum(q, 1e-9), 1.0)
        sp_p = sp["processor"] * IP
        IP = IP - sp_p
        S["demand"][t], S["orders_retail"][t], S["orders_proc"][t] = d.sum(), q.sum(), O.sum()
        S["sales"][t], S["unmet"][t], S["inv_retail"][t], S["inv_proc"][t] = sales.sum(), (d - sales).sum(), IR.sum(), IP.sum()
        S["delivered"][t], S["waste"][t], S["spoil"][t] = deliv.sum(), waste, sp_r.sum() + sp_p.sum()
        S["cost_hold"][t] = C["hold_retailer"] * IR.sum() + C["hold_processor"] * IP.sum()
        S["cost_short"][t], S["cost_spoil"][t], S["cost_waste"][t] = C["shortage"] * (d - sales).sum(), C["spoil"] * S["spoil"][t], C["raw_waste"] * waste
    return Result(compute_metrics(S, cfg, float(IR.sum() + IP.sum() + arr.sum()), initial_stock), S)


def compute_metrics(S: dict, cfg: dict, final_stock: float, initial_stock: float) -> dict:
    w = int(cfg["warmup_weeks"])
    ev = {k: v[w:] for k, v in S.items()}
    var = lambda x: float(np.var(x, ddof=1))  # noqa: E731
    ratio = lambda a, b: float("nan") if var(b) < 1e-12 else var(a) / var(b)  # noqa: E731  (undefined for constant demand)
    cost = ev["cost_hold"] + ev["cost_short"] + ev["cost_spoil"] + ev["cost_waste"]
    return {
        "fill_rate": float(ev["sales"].sum() / ev["demand"].sum()),
        "bullwhip_retail": ratio(ev["orders_retail"], ev["demand"]),
        "bullwhip_proc": ratio(ev["orders_proc"], ev["demand"]),
        "cost_per_week": float(cost.mean()),
        "cost_hold": float(ev["cost_hold"].mean()), "cost_short": float(ev["cost_short"].mean()),
        "cost_spoil": float(ev["cost_spoil"].mean()), "cost_waste": float(ev["cost_waste"].mean()),
        "unmet_per_week": float(ev["unmet"].mean()), "stockout_week_share": float((ev["unmet"] > 1e-9).mean()),
        "inv_retail": float(ev["inv_retail"].mean()), "inv_proc": float(ev["inv_proc"].mean()),
        "spoil_per_week": float(ev["spoil"].mean()), "waste_per_week": float(ev["waste"].mean()),
        "mass_balance_err": float(abs(S["delivered"].sum() - S["sales"].sum() - S["spoil"].sum() - (final_stock - initial_stock)) / max(S["delivered"].sum(), 1e-12)),
    }
