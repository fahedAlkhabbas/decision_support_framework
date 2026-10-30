"""
Multi-objective optimisation on top of the CP-SAT model.

Supported methods:
  * payoff table   - optimise each objective alone; gives the ideal point and
                     an estimate of the nadir point used for normalisation
  * weighted sum   - normalised weighted sum of objectives (architect-given weights)
  * lexicographic  - optimise objectives in priority order; each optimised
                     objective is then bounded (with an optional relative
                     tolerance) while the next one is optimised
  * Pareto front   - epsilon-constraint method for two objectives: minimise f1
                     subject to f2 <= eps, then minimise f2 subject to the
                     f1 value found (to obtain a non-dominated point),
                     and tighten eps until the problem becomes infeasible

Every solve builds a fresh model through `build_fn` so that bounds and
objectives of previous solves do not leak into the next one.
"""

import math

from core.metrics import OBJECTIVES
from solution.objectives import objective_expression


class MultiObjectiveOptimizer:

    def __init__(self, build_fn, knowledge_base, solution_manager):
        """
        Args:
            build_fn: callable() -> DeploymentModel with all constraints encoded
            knowledge_base: KnowledgeBase
            solution_manager: SolutionManager (solver parameters are taken from it)
        """
        self.build = build_fn
        self.kb = knowledge_base
        self.sm = solution_manager

    def _solve(self, objective, bounds=None, sense="min", **kw):
        dm = self.build()
        for name, ub in (bounds or {}).items():
            dm.model.Add(objective_expression(dm, self.kb, name) <= int(ub))
        return self.sm.solve(dm, objective, sense=sense, **kw)

    # ------------------------------------------------------------------ #
    def payoff_table(self, objectives=None):
        """
        Returns (rows, ideal, nadir) where rows[o] is the SolveResult of
        minimising objective o alone.
        """
        objectives = objectives or OBJECTIVES
        rows = {o: self._solve(o) for o in objectives}
        ok_rows = [r for r in rows.values() if r.ok]
        if not ok_rows:
            return rows, None, None
        ideal = {o: rows[o].metrics[o] for o in objectives if rows[o].ok}
        nadir = {o: max(r.metrics[o] for r in ok_rows) for o in objectives}
        return rows, ideal, nadir

    def weighted_sum(self, weights, ideal, nadir):
        """Minimise sum_i w_i (f_i - ideal_i)/(nadir_i - ideal_i)."""
        return self._solve("weighted", weights=weights, ideal=ideal, nadir=nadir)

    def lexicographic(self, priorities):
        """
        priorities: list of (objective, relative_tolerance), e.g.
            [("energy", 0.05), ("latency", 0.0)]
        allows up to 5% more energy than the optimum to improve latency.
        Returns the final SolveResult and the list of intermediate results.
        """
        bounds, steps = {}, []
        res = None
        for name, tol in priorities:
            res = self._solve(name, bounds=dict(bounds))
            steps.append(res)
            if not res.ok:
                break
            bounds[name] = math.floor(res.metrics[name] * (1 + tol))
        return res, steps

    def pareto_front(self, f1, f2, max_points=15):
        """
        Epsilon-constraint Pareto front for (f1, f2), both minimised.
        Returns the list of non-dominated SolveResults sorted by f1.
        """
        # A point is a proven Pareto-optimal point only if BOTH solves of the
        # two-stage epsilon-constraint step were solved to optimality. Otherwise
        # its status is downgraded to FEASIBLE (valid, but not proven non-dominated).
        def _two_stage(first, second):
            if first.status != "OPTIMAL" and second.ok:
                second.status = "FEASIBLE"
            return second

        # Extreme points
        best_f2 = self._solve(f2)
        if not best_f2.ok:
            return []
        lo2 = best_f2.metrics[f2]
        a0 = self._solve(f1)
        if not a0.ok:
            return []
        a = _two_stage(a0, self._solve(f2, bounds={f1: a0.metrics[f1]}))   # non-dominated f1-optimum
        hi2 = a.metrics[f2]
        step = max(1, math.ceil((hi2 - lo2) / max(1, max_points - 1)))

        points = [a]
        eps = hi2 - step
        while eps >= lo2 and len(points) < max_points:
            r0 = self._solve(f1, bounds={f2: eps})
            if not r0.ok:
                break
            r = _two_stage(r0, self._solve(f2, bounds={f1: r0.metrics[f1], f2: eps}))
            if not r.ok:
                break
            points.append(r)
            eps = min(eps, r.metrics[f2]) - step
        if all(p.metrics[f2] > lo2 for p in points):
            # non-dominated f2-optimum: minimise f1 among the deployments with f2 = lo2
            b = self._solve(f1, bounds={f2: lo2})
            points.append(_two_stage(best_f2, b) if b.ok else best_f2)
        return non_dominated(points, f1, f2)


def non_dominated(results, f1, f2):
    """Filter dominated results and duplicates; sort by f1."""
    pts = sorted(results, key=lambda r: (r.metrics[f1], r.metrics[f2]))
    front, best2 = [], math.inf
    for r in pts:
        if r.metrics[f2] < best2:
            front.append(r)
            best2 = r.metrics[f2]
    return front
