"""Figures from the result CSVs."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

PAL = {"none": "#d95f02", "pos": "#e6ab02", "vmi": "#7570b3", "full": "#1b9e77", "central": "#333333"}
ORDER = ["none", "pos", "vmi", "full", "central"]


def _save(fig, out, name):
    fig.tight_layout()
    fig.savefig(out / name, dpi=160)
    plt.close(fig)
    return out / name


def fig_example(res, out):
    d = pd.read_csv(res / "example_series.csv")
    regs = list(dict.fromkeys(d.regime))
    fig, ax = plt.subplots(1, len(regs), figsize=(4.6 * len(regs), 3.8), sharey=True, squeeze=False)
    for a, r in zip(ax[0], regs, strict=True):
        g = d[d.regime == r]
        a.plot(g.week, g.demand, color="#999999", lw=1.2, label="consumer demand")
        a.plot(g.week, g.orders_retail, color="#1b9e77", lw=1.0, label="retail orders")
        a.plot(g.week, g.orders_proc, color="#d95f02", lw=1.0, label="processor raw orders")
        a.set_title(r, fontsize=10)
        a.set_xlabel("week")
    ax[0][0].set_ylabel("units per week")
    ax[0][0].legend(fontsize=7)
    return _save(fig, out, "fig1_example_series.png")


def fig_regimes(res, out):
    d = pd.read_csv(res / "regimes.csv")
    d = d[d.variant == "tuned"]
    regs = [r for r in ORDER if r in set(d.regime)]
    fig, ax = plt.subplots(1, 4, figsize=(15, 3.8))
    for a, (col, lab) in zip(ax, (("bullwhip_retail", "Retail bullwhip (order var / demand var)"), ("bullwhip_proc", "Processor bullwhip"), ("fill_rate", "Fill rate"), ("cost_per_week", "Cost per week")), strict=True):
        bp = a.boxplot([d[d.regime == r][col] for r in regs], patch_artist=True, tick_labels=regs, widths=0.6)
        for patch, r in zip(bp["boxes"], regs, strict=True):
            patch.set_facecolor(PAL[r])
            patch.set_alpha(0.7)
        a.set_title(lab, fontsize=9)
        a.tick_params(axis="x", labelsize=8)
    return _save(fig, out, "fig2_regimes.png")


def _lines(df, xcol, cols, labels, name, out, xlabel):
    fig, ax = plt.subplots(1, len(cols), figsize=(4.6 * len(cols), 3.8), squeeze=False)
    for a, col, lab in zip(ax[0], cols, labels, strict=True):
        for r in [x for x in ORDER if x in set(df.regime)]:
            g = df[df.regime == r].groupby(xcol)[col].mean()
            a.plot(g.index, g.values, "-o", color=PAL[r], label=r, ms=4)
        a.set_xlabel(xlabel)
        a.set_title(lab, fontsize=9)
    ax[0][0].legend(fontsize=8)
    return _save(fig, out, name)


def fig_policy_map(res, out):
    m = pd.read_csv(res / "policy_map.csv")
    regs = list(dict.fromkeys(m.regime))
    fig, ax = plt.subplots(1, len(regs), figsize=(5 * len(regs), 3.8), squeeze=False)
    for a, r in zip(ax[0], regs, strict=True):
        p = m[m.regime == r].groupby(["alpha_retailer", "beta"])["bullwhip_proc"].mean().unstack()
        im = a.imshow(p.values, origin="lower", cmap="viridis", aspect="auto")
        a.set_xticks(range(len(p.columns)))
        a.set_xticklabels(p.columns)
        a.set_yticks(range(len(p.index)))
        a.set_yticklabels(p.index)
        a.set_xlabel("order smoothing beta")
        a.set_ylabel("retailer forecast weight alpha")
        a.set_title(f"{r}: processor bullwhip", fontsize=9)
        for (i, j), v in np.ndenumerate(p.values):
            a.text(j, i, f"{v:.2f}", ha="center", va="center", color="w", fontsize=8)
        fig.colorbar(im, ax=a)
    return _save(fig, out, "fig4_policy_map.png")


def make_all(res, out):
    res, out = Path(res), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    s, g, f = pd.read_csv(res / "shock_sweep.csv"), pd.read_csv(res / "gaming.csv"), pd.read_csv(res / "forecast_noise.csv")
    return [fig_example(res, out), fig_regimes(res, out),
            _lines(s, "shock_scale", ["fill_rate", "cost_per_week", "bullwhip_proc"], ["Fill rate", "Cost per week", "Processor bullwhip"], "fig3_shock_sweep.png", out, "climate-shock scale"),
            fig_policy_map(res, out),
            _lines(g, "gaming", ["bullwhip_retail", "fill_rate"], ["Retail bullwhip", "Fill rate"], "fig5_gaming.png", out, "shortage-gaming strength"),
            _lines(f, "forecast_noise", ["cost_per_week", "fill_rate"], ["Cost per week", "Fill rate"], "fig6_forecast_quality.png", out, "supply-forecast noise")]
