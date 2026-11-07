"""Markdown tables from the result CSVs (paired comparisons use common random numbers: the same world for every regime)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ORDER = ["none", "pos", "vmi", "full", "central"]


def md(df: pd.DataFrame) -> str:
    df = df.copy()
    df.columns = [str(c) for c in df.columns]
    rows = ["| " + " | ".join(df.columns) + " |", "|" + "|".join("---" for _ in df.columns) + "|"]
    rows += ["| " + " | ".join(str(v) for v in r.values) + " |" for _, r in df.iterrows()]
    return "\n".join(rows)


def med(s, nd=2):
    return f"{s.median():.{nd}f} [{s.quantile(.25):.{nd}f}, {s.quantile(.75):.{nd}f}]"


def paired(a, b, nd=2, n_boot=2000) -> str:
    """Mean of a - b with a 95 % bootstrap interval."""
    d = np.asarray(a) - np.asarray(b)
    rng = np.random.default_rng(0)
    bs = [rng.choice(d, len(d)).mean() for _ in range(n_boot)]
    return f"{d.mean():+.{nd}f} [{np.percentile(bs, 2.5):+.{nd}f}, {np.percentile(bs, 97.5):+.{nd}f}]"


def _piv(df, col, regime):
    return df[df.regime == regime].sort_values("rep")[col].to_numpy()


def summarize(res) -> str:
    res, out = Path(res), []
    tj = json.loads((res / "tuned_policies.json").read_text())
    out.append("##### Tuned settings per condition (each regime is tuned separately, on calibration worlds with separate seeds)\n")
    rows = []
    for cond, t in tj.items():
        for r in [x for x in ORDER if x in t]:
            v = t[r]
            rows.append({"condition": cond, "regime": r, "cover (weeks)": v["cover"], "safety factor z": v["z"], "early-warning weight theta": v.get("theta"), "calibration cost/week": round(v["cost_per_week"], 1)})
    out.append(md(pd.DataFrame(rows)))
    d = pd.read_csv(res / "regimes.csv")
    tuned = d[d.variant == "tuned"]
    reg = [r for r in ORDER if r in set(tuned.regime)]
    out.append("\n##### E1: information regimes at their tuned settings (median [IQR] over worlds)\n")
    rows = []
    for r in reg:
        g = tuned[tuned.regime == r]
        rows.append({"regime": r, "fill rate": med(g.fill_rate, 3), "bullwhip retail": med(g.bullwhip_retail), "bullwhip processor": med(g.bullwhip_proc), "cost / week": med(g.cost_per_week, 1), "stockout weeks": med(g.stockout_week_share, 2)})
    out.append(md(pd.DataFrame(rows)))
    out.append("\n##### Paired differences against `none` (mean [95 % bootstrap interval] over worlds)\n")
    rows = []
    for r in [x for x in reg if x != "none"]:
        rows.append({"regime": r, "fill rate": paired(_piv(tuned, "fill_rate", r), _piv(tuned, "fill_rate", "none"), 3), "bullwhip retail": paired(_piv(tuned, "bullwhip_retail", r), _piv(tuned, "bullwhip_retail", "none")),
                     "bullwhip processor": paired(_piv(tuned, "bullwhip_proc", r), _piv(tuned, "bullwhip_proc", "none")), "cost / week": paired(_piv(tuned, "cost_per_week", r), _piv(tuned, "cost_per_week", "none"), 1)})
    out.append(md(pd.DataFrame(rows)))
    if "central" in reg:
        out.append("\n##### Price of decentralisation: cost per week relative to the centralised planner (mean excess in %, 95 % interval)\n")
        c = _piv(tuned, "cost_per_week", "central")
        out.append(md(pd.DataFrame([{"regime": r, "excess cost (%)": paired(100 * _piv(tuned, "cost_per_week", r) / c, 100 * np.ones_like(c), 1)} for r in reg if r != "central"])))
    out.append("\n##### Cost components per week (tuned, mean)\n")
    cc = tuned.groupby("regime", sort=False)[["cost_hold", "cost_short", "cost_spoil", "cost_waste"]].mean().reindex(reg).round(1)
    out.append(md(cc.rename(columns=lambda c: c.replace("cost_", "")).reset_index()))
    dd = d[d.variant == "default"].groupby("regime", sort=False)[["fill_rate", "bullwhip_retail", "bullwhip_proc", "cost_per_week"]].mean().reindex(reg).round(3)
    out.append("\n##### Same regimes with the untuned default settings (cover 2 weeks, z 1.28; mean), to show how much tuning matters\n")
    out.append(md(dd.reset_index()))
    s = pd.read_csv(res / "shock_sweep.csv")
    out.append("\n##### E2: climate-shock severity (mean over worlds): fill rate / cost per week\n")
    a = s.groupby(["shock_scale", "regime"], sort=False)[["fill_rate", "cost_per_week"]].mean().reset_index()
    a["v"] = a.apply(lambda r: f"{r.fill_rate:.3f} / {r.cost_per_week:.1f}", axis=1)
    out.append(md(a.pivot(index="shock_scale", columns="regime", values="v").reindex(columns=reg).reset_index()))
    m = pd.read_csv(res / "policy_map.csv")
    out.append("\n##### E3: processor bullwhip by retailer forecast reactivity (rows) and order smoothing beta (columns), mean over worlds\n")
    for r in dict.fromkeys(m.regime):
        a = m[m.regime == r].groupby(["alpha_retailer", "beta"])["bullwhip_proc"].mean().unstack().round(2)
        out.append(f"Regime **{r}**\n")
        out.append(md(a.reset_index()))
        out.append("")
    g = pd.read_csv(res / "gaming.csv")
    out.append("##### E4: shortage gaming (order inflation after a rationed shipment), strong climate stress: retail bullwhip / fill rate (mean)\n")
    a = g.groupby(["gaming", "regime"], sort=False)[["bullwhip_retail", "fill_rate"]].mean().reset_index()
    a["v"] = a.apply(lambda r: f"{r.bullwhip_retail:.2f} / {r.fill_rate:.3f}", axis=1)
    out.append(md(a.pivot(index="gaming", columns="regime", values="v").reset_index()))
    f = pd.read_csv(res / "forecast_noise.csv")
    out.append("\n##### E5: quality of the shared supply forecast (noise as a fraction of expected supply), strong climate stress: cost per week / fill rate (mean)\n")
    a = f.groupby(["forecast_noise", "regime"], sort=False)[["cost_per_week", "fill_rate"]].mean().reset_index()
    a["v"] = a.apply(lambda r: f"{r.cost_per_week:.1f} / {r.fill_rate:.3f}", axis=1)
    out.append(md(a.pivot(index="forecast_noise", columns="regime", values="v").reset_index()))
    return "\n".join(out)
