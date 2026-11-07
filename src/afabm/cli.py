"""Command line: python -m afabm <run|figures|summary|params>."""
from __future__ import annotations

import argparse


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="afabm", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="run the experiments (tuning first; resumable)")
    r.add_argument("--config", default="configs/default.yaml")
    r.add_argument("--out", default="results/metrics")
    r.add_argument("--only", nargs="+", choices=["regimes", "shock_sweep", "policy_map", "gaming", "forecast_noise"])
    f = sub.add_parser("figures")
    f.add_argument("--results", default="results/metrics")
    f.add_argument("--out", default="results/figures")
    s = sub.add_parser("summary")
    s.add_argument("--results", default="results/metrics")
    p = sub.add_parser("params", help="export every parameter with its provenance status")
    p.add_argument("--config", default="configs/default.yaml")
    p.add_argument("--out", default="data/parameters.csv")
    a = ap.parse_args(argv)
    if a.cmd == "run":
        from afabm.experiments import run_all

        run_all(a.config, a.out, a.only)
    elif a.cmd == "figures":
        from afabm.plotting import make_all

        for path in make_all(a.results, a.out):
            print("wrote", path)
    elif a.cmd == "summary":
        from afabm.summary import summarize

        print(summarize(a.results))
    else:
        from afabm.config import load_config
        from afabm.provenance import export_parameters

        print(len(export_parameters(load_config(a.config), a.out)), "parameters ->", a.out)


if __name__ == "__main__":
    main()
