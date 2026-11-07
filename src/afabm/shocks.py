"""Spatially correlated, tail-dependent, left-skewed regional supply shocks (same process as the companion repo agrifood-supply-chain-climate-risk)."""
from __future__ import annotations

import numpy as np
from scipy import stats

_U = np.linspace(1e-6, 1 - 1e-6, 20001)
R_EARTH = 6371.0088


def haversine_km(lat, lon):
    la, lo = np.radians(np.asarray(lat, float)), np.radians(np.asarray(lon, float))
    a = np.sin((la[None, :] - la[:, None]) / 2) ** 2 + np.cos(la)[:, None] * np.cos(la)[None, :] * np.sin((lo[None, :] - lo[:, None]) / 2) ** 2
    return 2 * R_EARTH * np.arcsin(np.sqrt(a))


def nearest_correlation(R, eps=1e-6):
    R = (R + R.T) / 2
    w, v = np.linalg.eigh(R)
    R2 = (v * np.clip(w, eps, None)) @ v.T
    d = np.sqrt(np.diag(R2))
    R2 = R2 / np.outer(d, d)
    return (R2 + R2.T) / 2


class ShockGenerator:
    """Student-t copula with exponential spatial correlation and skew-normal marginals (fractional supply change per year)."""

    def __init__(self, dist_km, corr_length_km=200.0, df=4.0, skew_a=-4.0, loc=0.08, scale=0.12):
        self.R, self.df = nearest_correlation(np.exp(-dist_km / corr_length_km)), df
        self.q = stats.skewnorm.ppf(_U, skew_a, loc, scale)

    def sample(self, n, rng):
        z = rng.multivariate_normal(np.zeros(len(self.R)), self.R, size=n, method="eigh")
        w = rng.chisquare(self.df, size=n) / self.df
        u = np.clip(stats.t.cdf(z / np.sqrt(w)[:, None], self.df), 1e-6, 1 - 1e-6)
        return np.interp(u, _U, self.q)
