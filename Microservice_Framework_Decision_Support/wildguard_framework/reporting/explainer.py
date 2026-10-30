"""
Explanations of deployment recommendations.

Provides, for a deployment:
  * a quality profile (all objectives + slack w.r.t. the system requirements)
  * per-service placement rationale: which tiers/nodes were eligible, which
    requirement excluded the others, and with which services it is co-located
  * tight (binding or near-binding) constraints: saturated nodes, hops and
    flows with little latency slack
and, between deployments:
  * a side-by-side comparison with the deltas of every quality attribute and
    the services that moved
  * trade-off rates along a Pareto front (e.g. "+8% energy buys -250 ms")
"""

from collections import Counter, defaultdict

from core.metrics import OBJECTIVES, OBJECTIVE_LABELS, hop_delay

TIERS = ("Edge", "Fog", "Cloud")
TIGHT = 0.9   # utilisation / SLA ratio above which a constraint is reported as tight


def _tier(caps, n):
    return caps[n].get("tier", "Unknown")


def placement_rationale(kb, constraint_manager, nodes, caps, system_nfrs, assignment):
    """Per-service explanation of where it could and does run."""
    out = {}
    host_of = defaultdict(list)
    for c, ns in assignment.items():
        for n in ns:
            host_of[n].append(c)
    total_per_tier = Counter(_tier(caps, n) for n in nodes)
    for c in kb.components:
        eligible = Counter()
        excluded = defaultdict(Counter)   # tier -> reason -> count
        for n in nodes:
            reasons = constraint_manager.ineligibility_reasons(c, n, caps, system_nfrs)
            if reasons:
                for r in reasons:
                    excluded[_tier(caps, n)][r] += 1
            else:
                eligible[_tier(caps, n)] += 1
        hosts = assignment.get(c, [])
        out[c] = {
            "hosts": [{"node": n, "tier": _tier(caps, n),
                       "co_located_with": sorted(x for x in host_of[n] if x != c)} for n in hosts],
            "eligible_per_tier": {t: f"{eligible[t]}/{total_per_tier[t]}" for t in TIERS},
            "excluded_per_tier": {t: dict(excluded[t]) for t in TIERS if excluded[t]},
            "requirements": dict(kb.comp_requirements[c]),
        }
    return out


def tight_constraints(kb, caps, comm, system_nfrs, assignment, metrics):
    """Constraints that are binding or nearly binding in this deployment."""
    tight = []
    load = defaultdict(lambda: defaultdict(int))
    for c, ns in assignment.items():
        for n in ns:
            for r, key in (("cpu", "cpu"), ("memory", "memory"), ("throughput", "throughput_cap")):
                load[n][key] += kb.comp_requirements[c].get(r, 0)
    for n, l in sorted(load.items()):
        for key, label in (("cpu", "CPU"), ("memory", "memory"), ("throughput_cap", "throughput")):
            cap = caps[n].get(key)
            if cap and l[key] / cap >= TIGHT:
                tight.append({"kind": "capacity", "where": n,
                              "detail": f"{label} {l[key]}/{cap} ({100 * l[key] / cap:.0f}%)"})
    for (c1, c2), sla in kb.latency_constraints.items():
        for n1 in assignment.get(c1, []):
            for n2 in assignment.get(c2, []):
                if n1 != n2:
                    d = hop_delay(caps, comm, n1, n2)
                    if d / sla >= TIGHT:
                        tight.append({"kind": "hop_latency", "where": f"{c1}->{c2}",
                                      "detail": f"{d} ms of {sla} ms SLA ({n1}->{n2})"})
    max_delay = system_nfrs["performance"]["max_delay"]
    for f, d in metrics["flow_delays"].items():
        if d / max_delay >= TIGHT:
            tight.append({"kind": "e2e_delay", "where": f, "detail": f"{d} of {max_delay} ms"})
    return tight


def quality_profile(metrics, system_nfrs):
    """Objective values and slack with respect to the system requirements."""
    max_delay = system_nfrs["performance"]["max_delay"]
    return {
        **{o: metrics[o] for o in OBJECTIVES},
        "worst_flow_delay_ms": metrics["worst_flow_delay"],
        "e2e_slack_ms": max_delay - metrics["worst_flow_delay"],
        "series_mtbf_h": metrics["series_mtbf_h"],
        "min_security_margin": metrics["min_security_margin"],
        "used_nodes": metrics["used_nodes"],
        "tiers": metrics["tiers"],
    }


def compare(label_a, res_a, label_b, res_b, caps):
    """Deltas of every quality attribute from A to B and the services that moved."""
    rows = []
    for o in OBJECTIVES + ["worst_flow_delay", "used_nodes"]:
        a, b = res_a.metrics[o], res_b.metrics[o]
        pct = (100.0 * (b - a) / a) if a else None
        rows.append({"attribute": o, label_a: a, label_b: b, "delta": b - a,
                     "delta_pct": None if pct is None else round(pct, 1)})
    moved = []
    for c in res_a.assignment:
        na, nb = res_a.assignment[c], res_b.assignment.get(c, [])
        if sorted(na) != sorted(nb):
            moved.append({"service": c,
                          "from": [f"{n} ({_tier(caps, n)})" for n in na],
                          "to": [f"{n} ({_tier(caps, n)})" for n in nb]})
    better = [r["attribute"] for r in rows if r["delta"] < 0 and r["attribute"] in OBJECTIVES]
    worse = [r["attribute"] for r in rows if r["delta"] > 0 and r["attribute"] in OBJECTIVES]
    return {"rows": rows, "moved": moved, "b_better_on": better, "b_worse_on": worse}


def tradeoff_sentence(label_a, res_a, label_b, res_b, f1, f2):
    """Human-readable trade-off between two deployments on objectives f1 and f2."""
    a1, b1 = res_a.metrics[f1], res_b.metrics[f1]
    a2, b2 = res_a.metrics[f2], res_b.metrics[f2]
    p1 = 100.0 * (b1 - a1) / a1 if a1 else 0.0
    p2 = 100.0 * (b2 - a2) / a2 if a2 else 0.0
    return (f"Moving from {label_a} to {label_b} changes {f1} by {b1 - a1:+} ({p1:+.1f}%) "
            f"and {f2} by {b2 - a2:+} ({p2:+.1f}%).")


def pareto_tradeoffs(front, f1, f2):
    """Marginal trade-off between consecutive Pareto-optimal deployments."""
    segs = []
    for p, q in zip(front, front[1:]):
        d1 = q.metrics[f1] - p.metrics[f1]
        d2 = q.metrics[f2] - p.metrics[f2]
        segs.append({
            "from": (p.metrics[f1], p.metrics[f2]),
            "to": (q.metrics[f1], q.metrics[f2]),
            f"delta_{f1}": d1, f"delta_{f2}": d2,
            "delta_pct_f1": round(100.0 * d1 / p.metrics[f1], 1) if p.metrics[f1] else None,
            "delta_pct_f2": round(100.0 * d2 / p.metrics[f2], 1) if p.metrics[f2] else None,
            "rate": (round(d1 / -d2, 3) if d2 else None),   # units of f1 paid per unit of f2 saved
        })
    return segs


def explain(kb, constraint_manager, nodes, caps, comm, system_nfrs, result):
    """Full explanation of one deployment (dict)."""
    return {
        "quality_profile": quality_profile(result.metrics, system_nfrs),
        "placement": placement_rationale(kb, constraint_manager, nodes, caps, system_nfrs,
                                         result.assignment),
        "tight_constraints": tight_constraints(kb, caps, comm, system_nfrs, result.assignment,
                                               result.metrics),
    }


# ---------------------------------------------------------------------- #
# Markdown rendering
# ---------------------------------------------------------------------- #
def to_markdown(title, explanation):
    qp = explanation["quality_profile"]
    lines = [f"## {title}", "", "### Quality profile", "",
             "| Attribute | Value |", "|---|---|"]
    for o in OBJECTIVES:
        lines.append(f"| {OBJECTIVE_LABELS[o]} | {qp[o]} |")
    lines += [f"| Worst flow delay (ms) | {qp['worst_flow_delay_ms']} (slack {qp['e2e_slack_ms']}) |",
              f"| Series MTBF of hosts (h) | {qp['series_mtbf_h']} |",
              f"| Min. security margin | {qp['min_security_margin']} |",
              f"| Used nodes | {qp['used_nodes']} {qp['tiers']} |", "",
              "### Placement rationale", "",
              "| Service | Host(s) | Eligible E/F/C | Main exclusion reasons | Co-located with |",
              "|---|---|---|---|---|"]
    for c, p in explanation["placement"].items():
        hosts = ", ".join(f"{h['node']}" for h in p["hosts"])
        el = " / ".join(p["eligible_per_tier"][t] for t in TIERS)
        reasons = "; ".join(
            f"{t}: " + ", ".join(f"{r} ({k})" for r, k in sorted(rs.items(), key=lambda x: -x[1]))
            for t, rs in p["excluded_per_tier"].items())
        co = ", ".join(sorted({x for h in p["hosts"] for x in h["co_located_with"]})) or "-"
        lines.append(f"| {c} | {hosts} | {el} | {reasons or '-'} | {co} |")
    lines += ["", "### Tight constraints (>= 90% of the limit)", ""]
    if explanation["tight_constraints"]:
        for t in explanation["tight_constraints"]:
            lines.append(f"- {t['kind']} at {t['where']}: {t['detail']}")
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def comparison_to_markdown(label_a, label_b, cmp):
    lines = [f"## {label_a} vs {label_b}", "",
             f"| Attribute | {label_a} | {label_b} | Delta | Delta % |", "|---|---|---|---|---|"]
    for r in cmp["rows"]:
        pct = "" if r["delta_pct"] is None else "{:+.1f}%".format(r["delta_pct"])
        lines.append(f"| {r['attribute']} | {r[label_a]} | {r[label_b]} | {r['delta']:+} | {pct} |")
    lines += ["", f"{label_b} is better on: {', '.join(cmp['b_better_on']) or '-'}; "
                  f"worse on: {', '.join(cmp['b_worse_on']) or '-'}.", "",
              "Services that moved:", ""]
    for m in cmp["moved"] or []:
        lines.append(f"- {m['service']}: {', '.join(m['from'])} -> {', '.join(m['to'])}")
    if not cmp["moved"]:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def diagnosis_to_markdown(diag):
    if diag["feasible"] is True:
        return "The problem is feasible.\n"
    if diag["feasible"] is None:
        return ("## Infeasibility diagnosis\n\nThe solver reached the time limit before deciding "
                "whether a deployment exists; no diagnosis is possible. Increase the time limit.\n")
    title = "Minimal set" if diag.get("complete", True) else "Set (proven conflicting, possibly not minimal)"
    lines = ["## Infeasibility diagnosis", "",
             f"{title} of conflicting constraint families: {', '.join(diag['conflict']) or '(placement only)'}",
             ""]
    if diag["relaxations"]:
        lines.append("Relaxing any one of the following families restores feasibility: "
                     + ", ".join(diag["relaxations"]))
    else:
        lines.append("No single family is proven to restore feasibility when relaxed alone.")
    if diag.get("undetermined"):
        lines.append("Undetermined (time limit reached): " + ", ".join(diag["undetermined"]))
    return "\n".join(lines) + "\n"
