"""
Reporting Manager: turns solver outputs and validation results into
human-readable deployment recommendations and explanations.

Responsible for:
- formatting deployment recommendations (where each service runs, which
  nodes are used, quality attributes achieved)
- explaining recommendations (placement rationale, tight constraints)
- comparing deployments and describing trade-offs
- reporting infeasibility diagnostics
"""

import json

from reporting import explainer


class ReportingManager:
    """
    Formats the generated topologies into human-readable suggestions that
    architects can read and analyse easily.
    """

    def __init__(self, verbose=True):
        self.verbose = verbose

    def _print(self, *args):
        if self.verbose:
            print(*args)

    @staticmethod
    def get_node_type(node):
        """Tier of a node: "Edge", "Fog", "Cloud", or "Unknown"."""
        for t in ("Edge", "Fog", "Cloud"):
            if node.startswith(f"{t}Node"):
                return t
        return "Unknown"

    def pretty_group_nodes(self, used_nodes):
        """Group nodes by tier."""
        grouped = {"Edge": [], "Fog": [], "Cloud": [], "Unknown": []}
        for n in used_nodes:
            grouped[self.get_node_type(n)].append(n)
        for k in grouped:
            grouped[k].sort()
        return grouped

    def print_used_nodes(self, title, used_nodes):
        self._print(title)
        grouped = self.pretty_group_nodes(used_nodes)
        for tier in ("Edge", "Fog", "Cloud"):
            names = grouped[tier]
            self._print(f"   {tier} ({len(names)}): " + (", ".join(names) if names else "-"))

    def report_topologies(self, result, valid=None, message=""):
        """Report a SolveResult."""
        if result.ok:
            gap = "" if result.gap is None else f"  Gap={100 * result.gap:.2f}%"
            self._print(f"   Status={result.status}  SolveTime={result.time_s:.3f}s  "
                        f"Energy={result.energy}{gap}")
            m = result.metrics
            self._print(f"   Latency(sum)={m['latency']} ms  Worst flow={m['worst_flow_delay']} ms  "
                        f"Cost={m['cost']}  Carbon={m['carbon']}  FailureRate={m['failure_rate']}  "
                        f"SecurityRisk={m['security_risk']}")
            self.print_used_nodes("   Used node list:", result.used_nodes)
        else:
            self._print(f"   No feasible deployment found (status {result.status}).")
        if valid is not None:
            self._print(f"   Validation: {message}")

    def report_deployment_assignment(self, assignment):
        self._print("\nComponent Deployment Assignment:")
        for component in sorted(assignment.keys()):
            nodes = assignment[component]
            if isinstance(nodes, str):
                nodes = [nodes]
            hosts = ", ".join(f"{n} ({self.get_node_type(n)})" for n in nodes)
            self._print(f"   {component:20s} -> {hosts}")

    # ------------------------------------------------------------------ #
    # Explanations
    # ------------------------------------------------------------------ #
    def explain(self, kb, constraint_manager, nodes, caps, comm, system_nfrs, result, title):
        exp = explainer.explain(kb, constraint_manager, nodes, caps, comm, system_nfrs, result)
        return exp, explainer.to_markdown(title, exp)

    def compare(self, label_a, res_a, label_b, res_b, caps):
        cmp = explainer.compare(label_a, res_a, label_b, res_b, caps)
        return cmp, explainer.comparison_to_markdown(label_a, label_b, cmp)

    def diagnosis(self, diag):
        return explainer.diagnosis_to_markdown(diag)

    @staticmethod
    def write_json(path, obj):
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(obj, fh, indent=1, default=str)

    # ------------------------------------------------------------------ #
    # Summary tables (used by main.py)
    # ------------------------------------------------------------------ #
    def format_metrics_table(self, results):
        """results: list of (nodes, t_feasible, e_feasible, t_min, e_min, t_max, e_max)."""
        if not results:
            return "No results to display"
        lines = [
            f"{'Nodes':>5} | {'F_Time':>7} | {'F_Energy':>9} | {'B_Time':>7} | {'B_Energy':>9} | "
            f"{'W_Time':>7} | {'W_Energy':>9} | {'Saved':>7}",
            "-" * 80,
        ]
        for (nc, tf, ef, tb, eb, tw, ew) in results:
            lines.append(f"{nc:>5} | {tf:7.2f} | {ef:9.0f} | {tb:7.2f} | {eb:9.0f} | "
                         f"{tw:7.2f} | {ew:9.0f} | {ew - eb:7.0f}")
        return "\n".join(lines)

    def print_summary_header(self):
        self._print("\n" + "=" * 80)
        self._print("DEPLOYMENT SUMMARY")
        self._print("=" * 80)

    def print_section_header(self, title):
        self._print(f"\n-- {title} --")
