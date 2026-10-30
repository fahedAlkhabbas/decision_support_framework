"""
Linear objective expressions over the CP-SAT variables.

Each expression evaluates to exactly the value computed by
core.metrics.compute_metrics for the same deployment.
"""

from core.metrics import OBJECTIVES, failure_coeff


def objective_expression(dm, kb, name):
    """Linear expression of objective `name` for DeploymentModel dm."""
    A, caps, nodes, comps = dm.A, dm.caps, dm.nodes, dm.components
    if name == "energy":
        return sum(caps[n]["energy"] * dm.used[n] for n in nodes)
    if name == "carbon":
        return sum(caps[n]["carbon"] * dm.used[n] for n in nodes)
    if name == "cost":
        return sum(caps[n]["cost_per_vcpu"] * kb.comp_requirements[c]["cpu"] * A[c, n]
                   for c in comps for n in nodes)
    if name == "latency":
        return sum(dm.flow_delay.values())
    if name == "failure_rate":
        return sum(failure_coeff(caps[n]["mtbf"]) * dm.used[n] for n in nodes)
    if name == "security_risk":
        return sum((100 - caps[n]["encryption_compliance"]) * A[c, n]
                   for c in comps for n in nodes)
    raise ValueError(f"Unknown objective '{name}'. Available: {OBJECTIVES}")


def weighted_expression(dm, kb, weights, ideal=None, nadir=None, scale=10 ** 6):
    """
    Normalised weighted sum  sum_i w_i * (f_i - ideal_i) / (nadir_i - ideal_i).
    CP-SAT needs integer coefficients, so each objective is multiplied by
    round(w_i * scale / range_i); the constant offsets are dropped (they do not
    change the optimum). Without ideal/nadir the raw weighted sum is used.
    """
    expr = 0
    for name, w in weights.items():
        if w == 0:
            continue
        if ideal is not None and nadir is not None:
            rng = max(1, nadir[name] - ideal[name])
            k = max(1, int(round(w * scale / rng)))
        else:
            k = int(round(w))
        expr += k * objective_expression(dm, kb, name)
    return expr
