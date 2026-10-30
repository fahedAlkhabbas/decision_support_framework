"""
Solution Manager: runs the CP-SAT solver and optimises the deployment.

Responsible for:
- running the solver with explicit, reproducible parameters (time limit,
  number of workers, random seed)
- single-objective optimisation (energy, latency, cost, carbon, failure rate,
  security risk; minimisation or maximisation)
- returning the solver status, the objective value, the best proven bound
  and the resulting optimality gap
- infeasibility diagnostics (which constraint families are in conflict)
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ortools.sat.python import cp_model

from core.metrics import OBJECTIVES, compute_metrics
from solution.objectives import objective_expression, weighted_expression


@dataclass
class SolveResult:
    status: str
    ok: bool
    time_s: float                      # wall-clock time of Solve()
    objective: Optional[str] = None
    sense: str = "min"
    objective_value: Optional[float] = None
    best_bound: Optional[float] = None
    gap: Optional[float] = None        # relative gap |obj - bound| / max(1, |obj|)
    assignment: Dict[str, List[str]] = field(default_factory=dict)
    used_nodes: List[str] = field(default_factory=list)
    metrics: Dict = field(default_factory=dict)
    model_stats: Dict = field(default_factory=dict)

    @property
    def energy(self):
        return self.metrics.get("energy", 0)

    def summary(self):
        d = {
            "status": self.status, "ok": self.ok, "time_s": round(self.time_s, 4),
            "objective": self.objective, "sense": self.sense,
            "objective_value": self.objective_value, "best_bound": self.best_bound,
            "gap": self.gap,
        }
        for k in OBJECTIVES + ["worst_flow_delay", "used_nodes", "series_mtbf_h", "min_security_margin"]:
            if k in self.metrics:
                d[k] = self.metrics[k]
        d.update({f"model_{k}": v for k, v in self.model_stats.items()})
        return d


class SolutionManager:
    """
    Executes the constraint-solving engine to identify a deployment topology
    that satisfies all constraints and, when an objective is specified,
    optimises it.
    """

    def __init__(self, knowledge_base, time_limit=30.0, workers=None, random_seed=0):
        """
        Args:
            knowledge_base: KnowledgeBase
            time_limit: solver time limit in seconds (None = no limit)
            workers: number of CP-SAT search workers (None = solver default,
                i.e. all cores)
            random_seed: CP-SAT random seed
        """
        self.kb = knowledge_base
        self.time_limit = time_limit
        self.workers = workers
        self.random_seed = random_seed

    # ------------------------------------------------------------------ #
    def _make_solver(self, time_limit=None, workers=None):
        solver = cp_model.CpSolver()
        p = solver.parameters
        p.log_search_progress = False
        tl = self.time_limit if time_limit is None else time_limit
        if tl is not None and tl > 0:
            p.max_time_in_seconds = float(tl)
        w = self.workers if workers is None else workers
        if w is not None:
            if hasattr(p, "num_workers"):
                p.num_workers = int(w)
            else:  # older OR-Tools versions
                p.num_search_workers = int(w)
        p.random_seed = int(self.random_seed)
        return solver

    @staticmethod
    def _status_name(status):
        return {
            cp_model.OPTIMAL: "OPTIMAL",
            cp_model.FEASIBLE: "FEASIBLE",
            cp_model.INFEASIBLE: "INFEASIBLE",
            cp_model.MODEL_INVALID: "MODEL_INVALID",
        }.get(status, "UNKNOWN")

    def set_objective(self, dm, objective, sense="min", weights=None, ideal=None, nadir=None):
        """
        Attach an objective to the model.

        objective:
          None / "feasible"         no objective (first feasible deployment)
          "minimize" / "maximize"   energy (backward compatible with v1)
          one of core.metrics.OBJECTIVES (with sense "min" or "max")
          "weighted"                normalised weighted sum (weights, ideal, nadir)
        """
        if objective in (None, "feasible"):
            dm.objective_name = None
            return None
        if objective in ("minimize", "maximize"):
            sense = "min" if objective == "minimize" else "max"
            objective = "energy"
        if objective == "weighted":
            expr = weighted_expression(dm, self.kb, weights, ideal, nadir)
        else:
            expr = objective_expression(dm, self.kb, objective)
        if sense == "min":
            dm.model.Minimize(expr)
        else:
            dm.model.Maximize(expr)
        dm.objective_name = objective
        return expr

    def solve(self, dm, objective=None, sense="min", weights=None, ideal=None, nadir=None,
              time_limit=None, workers=None):
        """Solve the model (optionally optimising an objective) and return a SolveResult."""
        if objective in ("minimize", "maximize"):
            sense = "min" if objective == "minimize" else "max"
            objective = "energy"
        self.set_objective(dm, objective, sense, weights, ideal, nadir)
        solver = self._make_solver(time_limit, workers)
        t0 = time.perf_counter()
        status = solver.Solve(dm.model)
        t1 = time.perf_counter()

        res = SolveResult(
            status=self._status_name(status),
            ok=status in (cp_model.OPTIMAL, cp_model.FEASIBLE),
            time_s=t1 - t0,
            objective=dm.objective_name,
            sense=sense,
            model_stats=dm.stats(),
        )
        if res.ok:
            res.assignment = {
                c: [n for n in dm.nodes if solver.Value(dm.A[c, n])] for c in dm.components
            }
            res.used_nodes = sorted({n for ns in res.assignment.values() for n in ns})
            res.metrics = compute_metrics(self.kb, dm.caps, dm.comm, dm.system_nfrs, res.assignment)
            if dm.objective_name is not None:
                res.objective_value = solver.ObjectiveValue()
                res.best_bound = solver.BestObjectiveBound()
                res.gap = abs(res.objective_value - res.best_bound) / max(1.0, abs(res.objective_value))
        return res

    # Backward-compatible API (v1)
    def solve_and_optimize(self, dm, objective="feasible"):
        """Returns (ok, time_taken, energy, used_nodes, result)."""
        res = self.solve(dm, objective)
        return res.ok, res.time_s, res.energy, res.used_nodes, res

    # ------------------------------------------------------------------ #
    # Infeasibility diagnostics
    # ------------------------------------------------------------------ #
    def diagnose_infeasibility(self, build_fn, families, time_limit=None):
        """
        Identify constraint families that cannot be satisfied together.

        1. The model is built with one assumption literal per family and solved;
           CP-SAT returns a subset of assumptions sufficient for infeasibility.
        2. That subset (or all families if the solver returned none) is reduced
           to a minimal conflicting set with a deletion filter: a family is
           dropped from the set if the remaining families are still infeasible.
        3. For every family of the conflict, we report whether relaxing it
           alone restores feasibility.

        Args:
            build_fn: callable(enabled_families, diagnostics) -> DeploymentModel
            families: enabled families of the infeasible problem

        Returns:
            dict with keys: feasible, conflict (list), relaxations (list), core_from_solver
        """
        families = list(families)
        dm = build_fn(families, True)
        solver = self._make_solver(time_limit, workers=1)
        status = solver.Solve(dm.model)
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return {"feasible": True, "conflict": [], "relaxations": [], "core_from_solver": [],
                    "undetermined": [], "complete": True}
        if status != cp_model.INFEASIBLE:
            # Time limit reached before (in)feasibility was decided: no diagnosis is possible.
            return {"feasible": None, "conflict": [], "relaxations": [], "core_from_solver": [],
                    "undetermined": list(families), "complete": False}

        core = []
        if status == cp_model.INFEASIBLE:
            idx_to_fam = {(lit.Index() if hasattr(lit, "Index") else lit.index): fam
                          for fam, lit in dm.family_literals.items()}
            try:
                core = [idx_to_fam[i] for i in solver.SufficientAssumptionsForInfeasibility()
                        if i in idx_to_fam]
            except Exception:  # pragma: no cover - depends on solver version
                core = []
        candidate = list(core) if core else list(families)

        def check(subset):
            """True: proven infeasible; False: a deployment was found; None: time limit."""
            d = build_fn(subset, False)
            s = self._make_solver(time_limit)
            st = s.Solve(d.model)
            if st == cp_model.INFEASIBLE:
                return True
            if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                return False
            return None

        # Deletion filter. A family is dropped only if the remaining families are
        # PROVEN infeasible; on a time-out the family is kept, so the reported set
        # is always proven conflicting (but possibly not minimal, see 'complete').
        # The always-on placement constraints are not a family; an empty set can
        # only be infeasible if the instance itself cannot host every service.
        conflict = list(candidate)
        complete = True
        for fam in list(candidate):
            trial = [f for f in conflict if f != fam]
            res = check(trial)
            if res is True:
                conflict = trial
            elif res is None:
                complete = False

        # A family is reported as a sufficient relaxation only if a deployment is
        # actually FOUND without it; time-outs are reported as undetermined.
        relaxations, undetermined = [], []
        for fam in conflict:
            res = check([f for f in families if f != fam])
            if res is False:
                relaxations.append(fam)
            elif res is None:
                undetermined.append(fam)
                complete = False

        return {"feasible": False, "conflict": conflict, "relaxations": relaxations,
                "core_from_solver": core, "undetermined": undetermined, "complete": complete}
