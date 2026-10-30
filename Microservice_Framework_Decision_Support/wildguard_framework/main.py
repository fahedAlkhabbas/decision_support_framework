"""
Main entry point of the framework: a single, explained deployment run.

Examples:
    python main.py                               # 40 nodes, seed 0, 30 s limit
    python main.py --nodes 20 --seed 3
    python main.py --nodes 20 --objective latency
    python main.py --nodes 10 --seed 3           # infeasible instance -> diagnosis

For the experiments of the paper use experiments/run_experiments.py.
"""

import argparse
import os
import sys

_framework_dir = os.path.dirname(os.path.abspath(__file__))
if _framework_dir not in sys.path:
    sys.path.insert(0, _framework_dir)

from ui.user_interface import UserInterface          # noqa: E402
from core.metrics import OBJECTIVES                   # noqa: E402


def run_scalability_tests(node_sizes=(40,), seed=0, time_limit=30.0, workers=None):
    """Feasible / min-energy / max-energy deployments (original demo, now seeded)."""
    ui = UserInterface(time_limit=time_limit, workers=workers)
    results = []
    for nc in node_sizes:
        ui.reporting_manager.print_section_header("FEASIBLE deployment (no objective)")
        ok_f, time_f, energy_f, _ = ui.run_deployment_scenario(nc, None, "feasible", seed)
        ui.reporting_manager.print_section_header("MIN-ENERGY deployment")
        ok_b, time_b, energy_b, _ = ui.run_deployment_scenario(nc, None, "minimize", seed)
        ui.reporting_manager.print_section_header("MAX-ENERGY deployment")
        ok_w, time_w, energy_w, _ = ui.run_deployment_scenario(nc, None, "maximize", seed)
        if ok_f and ok_b and ok_w:
            results.append((nc, time_f, energy_f, time_b, energy_b, time_w, energy_w))
    if results:
        ui.reporting_manager.print_summary_header()
        print(ui.reporting_manager.format_metrics_table(results))


def main(argv=None):
    p = argparse.ArgumentParser(description="Decision-support framework: single explained run")
    p.add_argument("--nodes", type=int, default=40)
    p.add_argument("--seed", type=int, default=0, help="infrastructure instance seed")
    p.add_argument("--objective", default="energy", choices=["feasible"] + OBJECTIVES)
    p.add_argument("--time-limit", type=float, default=30.0)
    p.add_argument("--workers", type=int, default=None)
    p.add_argument("--scenario", default=None, help="scenario JSON (default: Wildfire-IntelGuard)")
    p.add_argument("--demo", action="store_true", help="run the original feasible/min/max demo")
    args = p.parse_args(argv)

    if args.demo:
        run_scalability_tests((args.nodes,), args.seed, args.time_limit, args.workers)
        return

    ui = UserInterface(scenario_path=args.scenario, time_limit=args.time_limit, workers=args.workers)
    print(f"Scenario: {ui.kb.scenario_name}  nodes={args.nodes}  seed={args.seed}  "
          f"objective={args.objective}")
    ui.setup(args.nodes, seed=args.seed)
    res, violations = ui.solve(args.objective)
    if not res.ok:
        print(ui.reporting_manager.diagnosis(ui.diagnose()))
        return
    ui.reporting_manager.report_deployment_assignment(res.assignment)
    print()
    print(ui.explain(res, f"Deployment ({args.objective})")[1])


if __name__ == "__main__":
    main()
