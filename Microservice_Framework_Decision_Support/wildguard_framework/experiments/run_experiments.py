#!/usr/bin/env python3
"""
Reproducible experiment harness for the revised paper.

Usage (from the wildguard_framework directory):

    python experiments/run_experiments.py all            # every experiment, paper settings
    python experiments/run_experiments.py all --quick    # small smoke-test settings
    python experiments/run_experiments.py scalability --sizes 10 20 30 --seeds 0 1 2
    python experiments/run_experiments.py timelimit --limits 30 300 3600
    python experiments/run_experiments.py ablation
    python experiments/run_experiments.py multiobjective
    python experiments/run_experiments.py explain
    python experiments/run_experiments.py plots

Every row of every CSV records the instance seed, the solver seed, the number
of workers and the time limit. Runs append to the CSV files and skip rows that
already exist, so an interrupted campaign can be resumed by re-running the
same command.

Experiments
-----------
scalability     feasible / min-energy / max-energy deployments for growing
                infrastructures (Figs. 5-7 of the original manuscript), repeated
                over several seeded instances.
timelimit       min-energy deployments of the same instances with several time
                limits (30 s and 300 s): compares the energy of the deployments
                (fig_gap_vs_nodes) and records the lower bound proven by CP-SAT;
                summary.txt also reports the certified optimality gap
                (Reviewer 2, comment 1).
ablation        min-energy deployments with one constraint family / requirement
                category removed; each resulting deployment is re-checked against
                the full requirement set (Reviewer 1, comment 4).
multiobjective  payoff table over six objectives, Pareto fronts (energy vs
                latency / cost / carbon / failure rate), weighted-sum and
                lexicographic solutions (Reviewer 1, comments 2 and 5).
explain         explanation report (placement rationale, tight constraints,
                comparisons, trade-offs, infeasibility diagnosis) for one instance
                (Reviewer 1, comment 5).
plots           figures from the CSV files.
"""

import argparse
import csv
import json
import os
import platform
import statistics
import sys
import time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from ui.user_interface import UserInterface                                  # noqa: E402
from constraints.constraint_manager import FAMILIES, CATEGORIES               # noqa: E402
from core.metrics import OBJECTIVES                                           # noqa: E402
from infrastructure.generator_config import GeneratorConfig                   # noqa: E402
from reporting import explainer                                               # noqa: E402

# Bumped whenever the constraint model changes; results of different model
# versions must not be mixed in the same output folder.
MODEL_VERSION = "2.1"

PAPER = {
    "scalability": {"sizes": list(range(10, 101, 10)), "seeds": list(range(10))},
    "timelimit": {"sizes": list(range(10, 101, 10)), "seeds": list(range(5)), "limits": [30, 300]},
    "ablation": {"sizes": [10, 30], "seeds": list(range(5))},
    "multiobjective": {"sizes": [20], "seeds": list(range(3)), "points": 10},
    "explain": {"sizes": [20], "seeds": [0]},
}
QUICK = {
    "scalability": {"sizes": [10, 20], "seeds": [0, 1]},
    "timelimit": {"sizes": [10, 20], "seeds": [0], "limits": [5, 20]},
    "ablation": {"sizes": [10], "seeds": [0]},
    "multiobjective": {"sizes": [10], "seeds": [0], "points": 4},
    "explain": {"sizes": [10], "seeds": [0]},
}

FIELDS = [
    "experiment", "variant", "nodes", "seed", "solver_seed", "workers", "time_limit",
    "mode", "status", "ok", "valid", "violations", "time_s",
    "objective_value", "best_bound", "gap",
] + OBJECTIVES + [
    "worst_flow_delay", "used_nodes", "edge_used", "fog_used", "cloud_used",
    "series_mtbf_h", "min_security_margin",
    "model_variables", "model_constraints", "model_placement_vars", "model_hop_vars",
    "links", "extra",
]


# ---------------------------------------------------------------------- #
# CSV helpers
# ---------------------------------------------------------------------- #
class CsvLog:
    def __init__(self, path, key_fields):
        self.path = path
        self.key_fields = key_fields
        self.done = set()
        if os.path.exists(path):
            with open(path, newline="") as fh:
                for row in csv.DictReader(fh):
                    self.done.add(tuple(str(row[k]) for k in key_fields))

    def has(self, **key):
        return tuple(str(key[k]) for k in self.key_fields) in self.done

    def write(self, row):
        new = not os.path.exists(self.path)
        with open(self.path, "a", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
            if new:
                w.writeheader()
            w.writerow(row)
        self.done.add(tuple(str(row[k]) for k in self.key_fields))


def read_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def filt(rows, cfg):
    """Keep only rows of the configured sizes and seeds (protects figures and
    summaries from rows of other campaigns stored in the same folder)."""
    sizes = {str(x) for x in cfg["sizes"]}
    seeds = {str(x) for x in cfg["seeds"]}
    return [r for r in rows if r["nodes"] in sizes and str(r["seed"]) in seeds]


def result_row(exp, variant, ui, args, res, violations, time_limit, mode, extra=None):
    m = res.metrics
    row = {
        "experiment": exp, "variant": variant, "nodes": len(ui.nodes),
        "seed": ui.infra_manager.seed, "solver_seed": args.solver_seed,
        "workers": args.workers if args.workers is not None else "default",
        "time_limit": time_limit, "mode": mode, "status": res.status, "ok": int(res.ok),
        "valid": int(res.ok and not violations), "violations": len(violations),
        "time_s": round(res.time_s, 4),
        "objective_value": res.objective_value, "best_bound": res.best_bound,
        "gap": None if res.gap is None else round(res.gap, 6),
        "links": ui.infra_manager.link_count(),
        "extra": json.dumps(extra) if extra else "",
    }
    for k, v in res.model_stats.items():
        row[f"model_{k}"] = v
    if res.ok:
        for o in OBJECTIVES + ["worst_flow_delay", "used_nodes", "series_mtbf_h", "min_security_margin"]:
            row[o] = m[o]
        row["edge_used"], row["fog_used"], row["cloud_used"] = (m["tiers"][t] for t in ("Edge", "Fog", "Cloud"))
    return row


def make_ui(args, time_limit=None):
    cfg = GeneratorConfig(heterogeneous=not args.homogeneous)
    return UserInterface(
        scenario_path=args.scenario, generator_config=cfg,
        time_limit=args.time_limit if time_limit is None else time_limit,
        workers=args.workers, solver_seed=args.solver_seed, verbose=False)


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


# ---------------------------------------------------------------------- #
# Experiments
# ---------------------------------------------------------------------- #
def exp_scalability(args, cfg):
    out = CsvLog(os.path.join(args.out, "scalability.csv"), ["nodes", "seed", "mode", "time_limit"])
    ui = make_ui(args)
    modes = [("feasible", "feasible", "min"), ("min_energy", "energy", "min"), ("max_energy", "energy", "max")]
    for n in cfg["sizes"]:
        for s in cfg["seeds"]:
            ui.setup(n, seed=s)
            for mode, obj, sense in modes:
                if out.has(nodes=n, seed=s, mode=mode, time_limit=args.time_limit):
                    continue
                res, viol = ui.solve(obj, sense=sense, report=False)
                out.write(result_row("scalability", "full", ui, args, res, viol, args.time_limit, mode))
                log(f"scalability n={n} seed={s} {mode}: {res.status} t={res.time_s:.2f}s "
                    f"E={res.energy} gap={res.gap}")


def exp_timelimit(args, cfg):
    out = CsvLog(os.path.join(args.out, "timelimit.csv"), ["nodes", "seed", "time_limit"])
    for n in cfg["sizes"]:
        for s in cfg["seeds"]:
            for tl in cfg["limits"]:
                if out.has(nodes=n, seed=s, time_limit=tl):
                    continue
                ui = make_ui(args, time_limit=tl if tl > 0 else None)
                ui.setup(n, seed=s)
                res, viol = ui.solve("energy", report=False)
                out.write(result_row("timelimit", "full", ui, args, res, viol, tl, "min_energy"))
                log(f"timelimit n={n} seed={s} limit={tl}s: {res.status} t={res.time_s:.1f}s "
                    f"E={res.energy} bound={res.best_bound} gap={res.gap}")


def ablation_variants():
    v = [("full", list(FAMILIES), "energy")]
    v += [(f"-{f}", [x for x in FAMILIES if x != f], "energy") for f in FAMILIES]
    v += [(f"-{c}", [x for x in FAMILIES if x not in fams], "energy") for c, fams in CATEGORIES.items()]
    v += [("-energy_objective", list(FAMILIES), "feasible")]
    return v


def exp_ablation(args, cfg):
    out = CsvLog(os.path.join(args.out, "ablation.csv"), ["nodes", "seed", "variant"])
    ui = make_ui(args)
    for n in cfg["sizes"]:
        for s in cfg["seeds"]:
            ui.setup(n, seed=s)
            for name, fams, obj in ablation_variants():
                if out.has(nodes=n, seed=s, variant=name):
                    continue
                res, viol = ui.solve(obj, enabled_families=fams, report=False)
                by_fam = ui.validation_manager.violations_by_family(viol)
                extra = {"violated_families": {k: c for k, c in by_fam.items() if c}}
                out.write(result_row("ablation", name, ui, args, res, viol, args.time_limit,
                                     "min_energy" if obj == "energy" else "feasible", extra))
                log(f"ablation n={n} seed={s} {name}: {res.status} t={res.time_s:.2f}s "
                    f"E={res.energy} violations={len(viol)} {extra['violated_families']}")


def exp_multiobjective(args, cfg):
    payoff = CsvLog(os.path.join(args.out, "mo_payoff.csv"), ["nodes", "seed", "variant"])
    pareto = CsvLog(os.path.join(args.out, "mo_pareto.csv"), ["nodes", "seed", "variant", "extra"])
    ui = make_ui(args)
    for n in cfg["sizes"]:
        for s in cfg["seeds"]:
            ui.setup(n, seed=s)
            mo = ui.multi_objective()
            rows, ideal, nadir = mo.payoff_table()
            def check(r):  # independent validation of every multi-objective deployment
                return ui.validation_manager.verify_deployment(
                    r.assignment, ui.nodes, ui.caps, ui.comm, ui.system_nfrs) if r.ok else []
            for o, r in rows.items():
                if not payoff.has(nodes=n, seed=s, variant=f"min_{o}"):
                    payoff.write(result_row("multiobjective", f"min_{o}", ui, args, r, check(r),
                                            args.time_limit, f"min_{o}"))
            if ideal is None:
                log(f"multiobjective n={n} seed={s}: infeasible")
                continue
            # weighted sum (equal weights) and lexicographic example
            if payoff.has(nodes=n, seed=s, variant="weighted_equal"):
                continue
            w = mo.weighted_sum({o: 1.0 for o in OBJECTIVES}, ideal, nadir)
            payoff.write(result_row("multiobjective", "weighted_equal", ui, args, w, check(w),
                                    args.time_limit, "weighted", {"ideal": ideal, "nadir": nadir}))
            lex, _ = mo.lexicographic([("energy", 0.10), ("latency", 0.0)])
            payoff.write(result_row("multiobjective", "lex_energy10_latency", ui, args, lex, check(lex),
                                    args.time_limit, "lexicographic"))
            for f2 in ("latency", "cost", "carbon", "failure_rate"):
                front = mo.pareto_front("energy", f2, max_points=cfg["points"])
                for i, r in enumerate(front):
                    pareto.write(result_row("multiobjective", f"energy_vs_{f2}", ui, args, r, check(r),
                                            args.time_limit, "pareto", {"point": i}))
                log(f"pareto n={n} seed={s} energy vs {f2}: "
                    f"{[(r.metrics['energy'], r.metrics[f2]) for r in front]}")


def exp_explain(args, cfg):
    n, s = cfg["sizes"][0], cfg["seeds"][0]
    ui = make_ui(args)
    ui.setup(n, seed=s)
    md = [f"# Explanation report (Wildfire-IntelGuard, {n} nodes, seed {s})", ""]
    feas, _ = ui.solve("feasible", report=False)
    front = ui.multi_objective().pareto_front("energy", "latency", max_points=8) if feas.ok else []
    if not front:
        md.append("No feasible deployment.\n")
        md.append(ui.reporting_manager.diagnosis(ui.diagnose()))
        worst = None
    else:
        mine, minl = front[0], front[-1]       # non-dominated end points of the front
        worst = minl.metrics["worst_flow_delay"]
        md.append(ui.explain(mine, "Minimum-energy deployment")[1])
        md.append(ui.reporting_manager.compare("first-feasible", feas, "min-energy", mine, ui.caps)[1])
        md.append(ui.reporting_manager.compare("min-energy", mine, "min-latency", minl, ui.caps)[1])
        md += ["## Energy-latency trade-offs along the Pareto front", "",
               "| From (E, L) | To (E, L) | dEnergy | dLatency | Energy paid per ms saved |",
               "|---|---|---|---|---|"]
        for seg in explainer.pareto_tradeoffs(front, "energy", "latency"):
            md.append(f"| {seg['from']} | {seg['to']} | {seg['delta_energy']:+} ({seg['delta_pct_f1']:+}%) | "
                      f"{seg['delta_latency']:+} ({seg['delta_pct_f2']:+}%) | {seg['rate']} |")
        if len(front) >= 2:
            md += ["", explainer.tradeoff_sentence("the min-energy deployment", mine,
                                                    "the min-latency deployment", minl,
                                                    "energy", "latency"), ""]
    if worst is not None:
        # Diagnosis example: the end-to-end bound is tightened to 90% of the worst
        # flow delay of the min-latency deployment (an over-constrained requirement).
        bound = int(0.9 * worst)
        strict = dict(ui.system_nfrs)
        strict["performance"] = dict(strict["performance"], max_delay=bound)
        ui.setup(n, system_nfrs=strict, seed=s)
        md += [f"# Diagnosis example: end-to-end delay bound tightened to {bound} ms", "",
               ui.reporting_manager.diagnosis(ui.diagnose())]
    path = os.path.join(args.out, "explanation_report.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(md))
    log(f"explanation written to {path}")


# ---------------------------------------------------------------------- #
# Plots
# ---------------------------------------------------------------------- #
def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def aggregate(rows, key_fields, value):
    groups = defaultdict(list)
    for r in rows:
        v = _num(r.get(value))
        if r.get("ok") == "1" and v is not None:
            groups[tuple(r[k] for k in key_fields)].append(v)
    out = {}
    for k, vals in groups.items():
        out[k] = (statistics.mean(vals), statistics.stdev(vals) if len(vals) > 1 else 0.0, len(vals))
    return out


def summarise(args, settings):
    """Text/CSV summary tables (mean, std, n) used for the paper."""
    lines = []
    sc = filt(read_csv(os.path.join(args.out, "scalability.csv")), settings["scalability"])
    if sc:
        lines.append("== scalability (mean ± std over feasible instances) ==")
        t = aggregate(sc, ["nodes", "mode"], "time_s")
        e = aggregate(sc, ["nodes", "mode"], "energy")
        g = aggregate(sc, ["nodes", "mode"], "gap")
        feas = defaultdict(lambda: [0, 0])
        for r in sc:
            if r["mode"] == "feasible":
                feas[r["nodes"]][0] += int(r["ok"])
                feas[r["nodes"]][1] += 1
        for n in sorted({r["nodes"] for r in sc}, key=int):
            parts = [f"n={n:>3} feasible instances {feas[n][0]}/{feas[n][1]}"]
            for mode in ("feasible", "min_energy", "max_energy"):
                if (n, mode) in t:
                    parts.append(f"{mode}: t={t[n, mode][0]:.2f}±{t[n, mode][1]:.2f}s "
                                 f"E={e[n, mode][0]:.0f}±{e[n, mode][1]:.0f}"
                                 + (f" gap={100 * g[n, mode][0]:.2f}%" if (n, mode) in g else ""))
            lines.append(" | ".join(parts))
    limits_cfg = set(settings["timelimit"]["limits"])
    tl = [r for r in filt(read_csv(os.path.join(args.out, "timelimit.csv")), settings["timelimit"])
          if int(float(r["time_limit"])) in limits_cfg]
    if tl:
        lines.append("\n== time limit vs certified gap ==")
        by_inst = defaultdict(dict)
        for r in tl:
            if r["ok"] == "1":
                by_inst[(r["nodes"], r["seed"])][int(float(r["time_limit"]))] = r
        limits = sorted({int(float(r["time_limit"])) for r in tl})
        for n in sorted({k[0] for k in by_inst}, key=int):
            insts = [v for k, v in by_inst.items() if k[0] == n]
            parts = [f"n={n:>3}"]
            for L in limits:
                gaps, cert, diffs, opt = [], [], [], 0
                for inst in insts:
                    if L not in inst:
                        continue
                    lb = max(_num(x["best_bound"]) for x in inst.values())
                    e = _num(inst[L]["energy"])
                    gaps.append(_num(inst[L]["gap"]))
                    cert.append((e - lb) / e if e else 0.0)
                    opt += inst[L]["status"] == "OPTIMAL"
                    best = min(_num(x["energy"]) for x in inst.values())
                    diffs.append(e - best)
                if gaps:
                    parts.append(f"limit={L}s: optimal {opt}/{len(gaps)}, own gap mean={100 * statistics.mean(gaps):.2f}% "
                                 f"max={100 * max(gaps):.2f}%, certified gap mean={100 * statistics.mean(cert):.2f}% "
                                 f"max={100 * max(cert):.2f}%, energy above best found mean={statistics.mean(diffs):.1f}")
            lines.append(" | ".join(parts))
    ab = filt(read_csv(os.path.join(args.out, "ablation.csv")), settings["ablation"])
    if ab:
        lines.append("\n== ablation (per variant, over all instances) ==")
        full = {(r["nodes"], r["seed"]): r for r in ab if r["variant"] == "full" and r["ok"] == "1"}
        variants = [v for v, _, _ in ablation_variants()]
        for v in variants:
            rs = [r for r in ab if r["variant"] == v]
            if not rs:
                continue
            okr = [r for r in rs if r["ok"] == "1"]
            inval = sum(1 for r in okr if int(r["violations"]) > 0)
            fams = defaultdict(int)
            for r in okr:
                if r["extra"]:
                    for f, c in json.loads(r["extra"]).get("violated_families", {}).items():
                        fams[f] += 1
            dE = [(_num(r["energy"]) - _num(full[(r["nodes"], r["seed"])]["energy"])) /
                  _num(full[(r["nodes"], r["seed"])]["energy"]) * 100
                  for r in okr if (r["nodes"], r["seed"]) in full and r["energy"]]
            dt = [_num(r["time_s"]) for r in okr]
            lines.append(f"{v:28s} solved {len(okr)}/{len(rs)}  invalid w.r.t. full reqs {inval}/{len(okr)}  "
                         f"dEnergy vs full {statistics.mean(dE) if dE else float('nan'):+.1f}%  "
                         f"time {statistics.mean(dt) if dt else float('nan'):.2f}s  "
                         f"violated: {dict(fams)}")
    text = "\n".join(lines)
    path = os.path.join(args.out, "summary.txt")
    with open(path, "w") as fh:
        fh.write(text + "\n")
    print(text)
    log(f"summary written to {path}")


def make_plots(args, settings):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # Validated categorical slots 1-3 (light mode) + distinct markers/line styles,
    # so identity never relies on colour alone.
    S = [("#2a78d6", "o", "-"), ("#eb6834", "s", "--"), ("#1baf7a", "^", ":")]
    plt.rcParams.update({
        "font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": "#e4e3df", "grid.linewidth": 0.6,
        "axes.edgecolor": "#8a8984", "axes.labelcolor": "#0b0b0b",
        "xtick.color": "#52514e", "ytick.color": "#52514e", "lines.linewidth": 2,
        "lines.markersize": 5, "legend.frameon": False, "savefig.dpi": 300,
    })
    os.makedirs(os.path.join(args.out, "figures"), exist_ok=True)
    fig_path = lambda name: os.path.join(args.out, "figures", name)  # noqa: E731

    def series(ax, agg, mode, label, style, scale=1.0):
        xs = sorted({int(k[0]) for k in agg if k[1] == mode})
        if not xs:
            return
        ys = [agg[(str(x), mode)][0] * scale for x in xs]
        sd = [agg[(str(x), mode)][1] * scale for x in xs]
        c, mk, ls = style
        ax.errorbar(xs, ys, yerr=sd, color=c, marker=mk, linestyle=ls, capsize=3, label=label)

    sc = filt(read_csv(os.path.join(args.out, "scalability.csv")), settings["scalability"])
    if sc:
        t = aggregate(sc, ["nodes", "mode"], "time_s")
        fig, ax = plt.subplots(figsize=(3.4, 2.5))
        series(ax, t, "feasible", "Feasible deployment", S[0])
        series(ax, t, "min_energy", f"Min-energy ({args.time_limit:g} s limit)", S[1])
        ax.set_xlabel("Number of nodes")
        ax.set_ylabel("Solving time (s)")
        ax.legend(loc="upper left", fontsize=7)
        fig.tight_layout()
        fig.savefig(fig_path("fig_time_vs_nodes.pdf"))
        fig.savefig(fig_path("fig_time_vs_nodes.png"))
        plt.close(fig)

        e = aggregate(sc, ["nodes", "mode"], "energy")
        fig, ax = plt.subplots(figsize=(3.4, 2.8))
        series(ax, e, "max_energy", "Max-energy", S[2])
        series(ax, e, "feasible", "Feasible", S[0])
        series(ax, e, "min_energy", "Min-energy", S[1])
        ax.set_xlabel("Number of nodes")
        ax.set_ylabel("Energy consumption (units)")
        ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3, fontsize=7,
                  handlelength=1.8, columnspacing=1.0)
        fig.tight_layout()
        fig.savefig(fig_path("fig_energy_vs_nodes.pdf"))
        fig.savefig(fig_path("fig_energy_vs_nodes.png"))
        plt.close(fig)

    limits_cfg = set(settings["timelimit"]["limits"])
    tl = [r for r in filt(read_csv(os.path.join(args.out, "timelimit.csv")), settings["timelimit"])
          if int(float(r["time_limit"])) in limits_cfg]
    if tl:
        by_inst = defaultdict(dict)
        for r in tl:
            if r["ok"] == "1":
                by_inst[(int(r["nodes"]), r["seed"])][int(float(r["time_limit"]))] = r
        limits = sorted({int(float(r["time_limit"])) for r in tl})
        L0 = limits[0]
        # Energy of the minimum-energy deployments found with each time limit
        # (mean over the instances of each size; only instances solved by all limits).
        fig, ax = plt.subplots(figsize=(3.4, 2.5))
        sizes = sorted({k[0] for k in by_inst})
        for j, L in enumerate(limits):
            xs, ys = [], []
            for n in sizes:
                vals = [_num(inst[L]["energy"]) for (nn, _), inst in by_inst.items()
                        if nn == n and all(l in inst for l in limits)]
                if vals:
                    xs.append(n); ys.append(statistics.mean(vals))
            c, mk, ls = S[j]
            if j == 0:
                ax.plot(xs, ys, color=c, marker=mk, linestyle=ls, markersize=7,
                        label=f"{L}-second limit")
            else:
                ax.plot(xs, ys, color=c, marker="x", linestyle=ls, markersize=7,
                        markeredgewidth=1.6, label=f"{L}-second limit")
        ax.set_xticks(sizes)
        ax.grid(axis="y", alpha=0.3)
        ax.set_xlabel("Number of nodes")
        ax.set_ylabel("Energy consumption (units)")
        ax.legend(loc="upper right", fontsize=7)
        fig.tight_layout()
        fig.savefig(fig_path("fig_gap_vs_nodes.pdf"))
        fig.savefig(fig_path("fig_gap_vs_nodes.png"))
        plt.close(fig)

    ab = filt(read_csv(os.path.join(args.out, "ablation.csv")), settings["ablation"])
    if ab:
        variants = [v for v, _, _ in ablation_variants() if v != "full"]
        frac = []
        for v in variants:
            okr = [r for r in ab if r["variant"] == v and r["ok"] == "1"]
            frac.append(100 * sum(int(r["violations"]) > 0 for r in okr) / len(okr) if okr else 0)
        fig, ax = plt.subplots(figsize=(6.8, 2.8))
        ax.bar(range(len(variants)), frac, color=S[0][0], width=0.7)
        ax.set_xticks(range(len(variants)))
        ax.set_xticklabels([v.lstrip("-") for v in variants], rotation=60, ha="right", fontsize=7)
        ax.set_ylabel("Invalid deployments (%)")
        ax.set_ylim(0, 100)
        ax.grid(axis="x", visible=False)
        n_fam = len(FAMILIES)
        ax.axvline(n_fam - 0.5, color="#8a8984", linewidth=0.8, linestyle="--")
        ax.text((n_fam - 1) / 2, 104, "constraint families", ha="center", fontsize=7, color="#52514e")
        ax.text(n_fam + (len(variants) - n_fam - 1) / 2, 104, "categories / objective", ha="center",
                fontsize=7, color="#52514e")
        fig.tight_layout()
        fig.savefig(fig_path("fig_ablation.pdf"))
        fig.savefig(fig_path("fig_ablation.png"))
        plt.close(fig)

    pa = filt(read_csv(os.path.join(args.out, "mo_pareto.csv")), settings["multiobjective"])
    if pa:
        n0 = str(settings["multiobjective"]["sizes"][0])
        s0 = str(settings["multiobjective"]["seeds"][0])
        f2s = [f for f in ("latency", "cost", "carbon", "failure_rate")
               if any(r["variant"] == f"energy_vs_{f}" for r in pa)]
        if len(f2s) == 4:
            fig, axes = plt.subplots(2, 2, figsize=(5.6, 4.0))
            axes = list(axes.flat)
        else:
            fig, axes = plt.subplots(1, len(f2s), figsize=(1.9 * len(f2s) + 0.4, 2.3))
            axes = axes if len(f2s) > 1 else [axes]
        from core.metrics import OBJECTIVE_LABELS
        for ax, f2 in zip(axes, f2s):
            rs = [r for r in pa if r["variant"] == f"energy_vs_{f2}" and r["nodes"] == n0 and r["seed"] == s0]
            rs.sort(key=lambda r: _num(r["energy"]))
            ax.plot([_num(r["energy"]) for r in rs], [_num(r[f2]) for r in rs],
                    color=S[0][0], drawstyle="steps-post")
            # filled markers: proven Pareto-optimal; open markers: not proven within the time limit
            for proven in (True, False):
                pts = [r for r in rs if (r["status"] == "OPTIMAL") == proven]
                if pts:
                    ax.plot([_num(r["energy"]) for r in pts], [_num(r[f2]) for r in pts],
                            linestyle="none", marker="o", markersize=5, color=S[0][0],
                            markerfacecolor=S[0][0] if proven else "white", markeredgewidth=1.3)
            ax.set_xlabel("Energy (units)")
            ax.set_ylabel(OBJECTIVE_LABELS[f2], fontsize=8)
        fig.tight_layout()
        fig.savefig(fig_path("fig_pareto.pdf"))
        fig.savefig(fig_path("fig_pareto.png"))
        plt.close(fig)
    log(f"figures written to {os.path.join(args.out, 'figures')}")


# ---------------------------------------------------------------------- #
def write_run_info(args):
    try:
        import ortools
        ortools_version = ortools.__version__
    except Exception:  # pragma: no cover
        ortools_version = "unknown"
    info = {
        "started": time.strftime("%Y-%m-%d %H:%M:%S"),
        "platform": platform.platform(), "processor": platform.processor(),
        "machine": platform.machine(), "cpu_count": os.cpu_count(),
        "python": sys.version, "ortools": ortools_version,
        "model_version": MODEL_VERSION,
        "time_limit": args.time_limit, "workers": args.workers, "solver_seed": args.solver_seed,
        "scenario": args.scenario or "scenarios/wildfire_intelguard.json",
        "generator": GeneratorConfig(heterogeneous=not args.homogeneous).describe(),
        "settings": QUICK if args.quick else PAPER,
    }
    with open(os.path.join(args.out, "run_info.json"), "w") as fh:
        json.dump(info, fh, indent=1, default=str)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("experiment", choices=["all", "scalability", "timelimit", "ablation",
                                          "multiobjective", "explain", "plots", "summary"])
    p.add_argument("--out", default=None,
                   help="output folder (default: results/, or results_quick/ with --quick)")
    p.add_argument("--quick", action="store_true", help="small smoke-test settings")
    p.add_argument("--sizes", type=int, nargs="+", help="override infrastructure sizes")
    p.add_argument("--seeds", type=int, nargs="+", help="override instance seeds")
    p.add_argument("--limits", type=int, nargs="+", help="time limits for 'timelimit' (0 = none)")
    p.add_argument("--time-limit", type=float, default=30.0, help="solver time limit (s)")
    p.add_argument("--workers", type=int, default=None, help="CP-SAT workers (default: all cores)")
    p.add_argument("--solver-seed", type=int, default=0, help="CP-SAT random seed")
    p.add_argument("--scenario", default=None, help="scenario JSON file")
    p.add_argument("--homogeneous", action="store_true",
                   help="use the original homogeneous MTBF/encryption values")
    args = p.parse_args(argv)
    if args.out is None:
        args.out = os.path.join(ROOT, "results_quick" if args.quick else "results")
    os.makedirs(args.out, exist_ok=True)
    info_path = os.path.join(args.out, "run_info.json")
    if os.path.exists(info_path) and args.experiment not in ("plots", "summary"):
        with open(info_path) as fh:
            old = json.load(fh).get("model_version")
        if old != MODEL_VERSION and any(f.endswith(".csv") for f in os.listdir(args.out)):
            sys.exit(f"{args.out} contains results of model version {old}; this code is model "
                     f"version {MODEL_VERSION}. Use another --out folder or delete the old results.")
    write_run_info(args)

    base = QUICK if args.quick else PAPER
    settings = {k: dict(v) for k, v in base.items()}
    for k in settings:
        if args.sizes:
            settings[k]["sizes"] = args.sizes
        if args.seeds:
            settings[k]["seeds"] = args.seeds
    if args.limits:
        settings["timelimit"]["limits"] = args.limits

    runners = {
        "scalability": exp_scalability, "timelimit": exp_timelimit, "ablation": exp_ablation,
        "multiobjective": exp_multiobjective, "explain": exp_explain,
    }
    todo = list(runners) if args.experiment == "all" else \
        ([args.experiment] if args.experiment in runners else [])
    for name in todo:
        log(f"=== {name} ===")
        runners[name](args, settings[name])
    if args.experiment in ("all", "summary", "plots") or todo:
        summarise(args, settings)
    if args.experiment in ("all", "plots"):
        make_plots(args, settings)


if __name__ == "__main__":
    main()
