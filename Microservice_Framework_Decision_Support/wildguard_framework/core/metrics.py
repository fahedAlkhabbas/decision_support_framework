"""
Quality metrics of a deployment, computed directly from the assignment
(independently of the solver model). The same definitions are used to build
the optimisation objectives (solution/objectives.py), so that the reported
values and the optimised values coincide.

An assignment maps every service to the list of nodes hosting it (one entry
per replica): {service: [node, ...]}.

Objectives (all minimised):
  energy         sum of the energy cost of the used nodes
  carbon         sum over used nodes of energy x grid carbon intensity / 100
  cost           sum over placements of node cost-per-vCPU x service vCPUs
  latency        sum over data flows of the end-to-end flow delay (ms)
  failure_rate   sum over used nodes of round(1e6 / node MTBF): failure rate
                 (per 10^6 h) of the series system formed by the used nodes
                 (the system is down if any used node fails; replicas are
                 ignored, so this is a conservative estimate)
  security_risk  sum over placements of (100 - node encryption compliance)
"""

from collections import OrderedDict

NO_LINK_LATENCY = 10 ** 6

OBJECTIVES = ["energy", "latency", "cost", "carbon", "failure_rate", "security_risk"]

OBJECTIVE_LABELS = {
    "energy": "Energy (units)",
    "latency": "Sum of flow delays (ms)",
    "cost": "Cost (units/h)",
    "carbon": "Carbon (units)",
    "failure_rate": "Failure rate (1/10^6 h)",
    "security_risk": "Security risk (pts)",
}


def failure_coeff(mtbf):
    return int(round(1e6 / mtbf))


def hop_delay(caps, comm, n1, n2):
    if n1 == n2:
        return 2 * caps[n1]["proc_delay"]
    lat = comm.get((n1, n2), {}).get("latency", NO_LINK_LATENCY)
    return caps[n1]["proc_delay"] + lat + caps[n2]["proc_delay"]


def used_nodes(assignment):
    return sorted({n for ns in assignment.values() for n in ns})


def flow_delays(kb, caps, comm, assignment):
    """End-to-end delay (ms) of every data flow."""
    out = OrderedDict()
    for fname, chain in kb.dataflow_paths.items():
        total = sum(kb.comp_requirements[c]["response_time"] for c in chain)
        for c, d in zip(chain, chain[1:]):
            for n1 in assignment.get(c, []):
                for n2 in assignment.get(d, []):
                    total += hop_delay(caps, comm, n1, n2)
        out[fname] = total
    return out


def compute_metrics(kb, caps, comm, system_nfrs, assignment):
    """All quality metrics of a deployment (dict)."""
    used = used_nodes(assignment)
    placements = [(c, n) for c, ns in assignment.items() for n in ns]
    fd = flow_delays(kb, caps, comm, assignment)
    fr = sum(failure_coeff(caps[n]["mtbf"]) for n in used)
    m = OrderedDict()
    m["energy"] = sum(caps[n]["energy"] for n in used)
    m["latency"] = sum(fd.values())
    m["cost"] = sum(caps[n]["cost_per_vcpu"] * kb.comp_requirements[c]["cpu"] for c, n in placements)
    m["carbon"] = sum(caps[n]["carbon"] for n in used)
    m["failure_rate"] = fr
    m["security_risk"] = sum(100 - caps[n]["encryption_compliance"] for _, n in placements)
    # Derived, human-oriented indicators
    m["worst_flow_delay"] = max(fd.values()) if fd else 0
    m["flow_delays"] = dict(fd)
    m["series_mtbf_h"] = round(1e6 / fr, 1) if fr else float("inf")
    m["min_host_mtbf_h"] = min(caps[n]["mtbf"] for n in used) if used else None
    m["min_security_margin"] = (min(caps[n]["encryption_compliance"] for n in used)
                                - system_nfrs["security"]) if used else None
    m["used_nodes"] = len(used)
    m["tiers"] = {t: sum(1 for n in used if caps[n].get("tier") == t) for t in ("Edge", "Fog", "Cloud")}
    return m
