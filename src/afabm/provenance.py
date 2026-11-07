"""Export every numeric parameter with an honest provenance status."""
from __future__ import annotations

import pandas as pd


def _flatten(d, prefix=""):
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            yield from _flatten(v, key + ".")
        elif isinstance(v, list):
            yield key, str(v)
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            yield key, v


def export_parameters(cfg: dict, path) -> pd.DataFrame:
    skip = {"experiments", "regimes"}
    rows = []
    for key, v in _flatten({k: x for k, x in cfg.items() if k not in skip}):
        note = "climate-shock process: same illustrative process as the companion supply-chain repository" if key.startswith("climate") else "illustrative; not calibrated to any firm or dataset"
        rows.append({"key": key, "value": v, "status": "illustrative", "note": note})
    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)
    return df
