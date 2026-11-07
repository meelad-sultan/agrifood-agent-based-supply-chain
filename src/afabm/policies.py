"""Agent decision rules and the centralised benchmark planner."""
from __future__ import annotations

import numpy as np
from scipy.optimize import linprog


def proportional(avail: float, requests: np.ndarray) -> np.ndarray:
    """Allocate ``avail`` among requests pro rata (rationing); never more than requested."""
    tot = float(requests.sum())
    return requests * min(1.0, avail / tot) if tot > 1e-12 else requests * 0.0


def smooth(mu, var, x, alpha, alpha_sigma):
    """Exponential smoothing of the level and of the squared one-step forecast error (error uses the previous level)."""
    err = x - mu
    return alpha * x + (1 - alpha) * mu, alpha_sigma * err**2 + (1 - alpha_sigma) * var


def order_up_to(mu, var, position, cover, z, beta):
    """Base-stock order with order smoothing: beta = 1 is pure order-up-to, beta < 1 moves gradually from the forecast toward the target."""
    target = mu * cover + z * np.sqrt(var * cover)
    return np.maximum(0.0, (1 - beta) * mu + beta * (target - position))


def central_plan(ip0, ir0, t, world, cfg):
    """One decision of the centralised planner: a rolling-horizon linear programme on the pooled chain.

    Decides this week's raw intake x and shipments y to retail, knowing the planner's (possibly noisy) supply forecast and the demand
    distribution. Variables per week tau: x (raw intake), y (shipments), sal (sales next week), PI / RI (processor / retail inventory
    after the week). Returns (x0, y0).
    """
    pc, sf = cfg["policy"]["central"], cfg["policy"]["supply_forecast"]
    H, z, C, sp = int(pc["horizon_weeks"]), pc["z"], cfg["costs"], cfg["spoilage"]
    sR, sP = sp["retailer"], sp["processor"]
    T = world.T
    k_tot = float(sum(cfg["processors"]["capacity"]))
    sup = world.supply_expect[np.minimum(t + np.arange(H), T - 1)] * (1 + sf["noise_cv"] * world.fc_eps[t, :H])
    sup[0] = world.supply[t].sum()
    didx = np.minimum(t + 1 + np.arange(H), T - 1)
    dplan = world.mean_demand[didx].sum(1) + z * world.sigma_total[didx]
    nv = 5 * H
    X, Y, S, PI, RI = (np.arange(i * H, (i + 1) * H) for i in range(5))
    A_ub, b_ub, A_eq, b_eq = [], [], [], []
    for k in range(H):
        r = np.zeros(nv); r[Y[k]] = 1; r[X[k]] = -1
        if k:
            r[PI[k - 1]] = -1
        A_ub.append(r); b_ub.append(ip0 if k == 0 else 0.0)
        r = np.zeros(nv); r[S[k]] = 1; r[Y[k]] = -1
        if k:
            r[RI[k - 1]] = -1
        A_ub.append(r); b_ub.append(ir0 if k == 0 else 0.0)
        r = np.zeros(nv); r[PI[k]] = 1; r[X[k]] = -(1 - sP); r[Y[k]] = 1 - sP
        if k:
            r[PI[k - 1]] = -(1 - sP)
        A_eq.append(r); b_eq.append((1 - sP) * ip0 if k == 0 else 0.0)
        r = np.zeros(nv); r[RI[k]] = 1; r[Y[k]] = -(1 - sR); r[S[k]] = 1 - sR
        if k:
            r[RI[k - 1]] = -(1 - sR)
        A_eq.append(r); b_eq.append((1 - sR) * ir0 if k == 0 else 0.0)
    c = np.zeros(nv); c[S] = -C["shortage"]; c[RI] = C["hold_retailer"]; c[PI] = C["hold_processor"]; c[X] = 0.01
    bounds = [(0, min(float(sup[k]), k_tot)) for k in range(H)] + [(0, None)] * H + [(0, float(dplan[k])) for k in range(H)] + [(0, None)] * (2 * H)
    res = linprog(c, A_ub=np.array(A_ub), b_ub=b_ub, A_eq=np.array(A_eq), b_eq=b_eq, bounds=bounds, method="highs")
    if res.status != 0:  # cannot happen with x = y = 0 feasible; kept as a safe fallback
        x0 = min(float(sup[0]), k_tot)
        return x0, min(ip0 + x0, float(dplan[0]))
    return float(res.x[X[0]]), float(res.x[Y[0]])
