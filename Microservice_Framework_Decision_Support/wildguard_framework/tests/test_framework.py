"""
Tests for the framework. Run from the wildguard_framework directory:

    python -m pytest tests -q

Solver-based tests are skipped when OR-Tools is not installed.
"""

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.knowledge_base import KnowledgeBase                     # noqa: E402
from core.metrics import OBJECTIVES, compute_metrics              # noqa: E402
from infrastructure.infrastructure_manager import InfrastructureManager  # noqa: E402
from infrastructure.generator_config import GeneratorConfig      # noqa: E402
from validation.validation_manager import ValidationManager      # noqa: E402

try:
    import ortools  # noqa: F401
    HAVE_ORTOOLS = True
except ImportError:
    HAVE_ORTOOLS = False

needs_solver = pytest.mark.skipif(not HAVE_ORTOOLS, reason="OR-Tools not installed")


# ---------------------------------------------------------------------- #
# Generator
# ---------------------------------------------------------------------- #
def test_generator_is_deterministic():
    a = InfrastructureManager().instantiate_infrastructure(30, seed=7)
    b = InfrastructureManager().instantiate_infrastructure(30, seed=7)
    assert a == b
    c = InfrastructureManager().instantiate_infrastructure(30, seed=8)
    assert a[1] != c[1]


def test_tier_shares_and_connectivity():
    nodes, caps, comm = InfrastructureManager().instantiate_infrastructure(50, seed=1)
    tiers = [caps[n]["tier"] for n in nodes]
    assert tiers.count("Edge") == 30 and tiers.count("Fog") == 15 and tiers.count("Cloud") == 5
    for n in nodes:
        if caps[n]["tier"] == "Edge":
            assert sum(1 for m in nodes if caps[m]["tier"] == "Fog" and (n, m) in comm) >= 3
    for (a, b), props in comm.items():
        assert comm[(b, a)] == props


def test_extended_attributes_do_not_change_core_instance():
    het = InfrastructureManager(GeneratorConfig(heterogeneous=True)).instantiate_infrastructure(20, seed=3)
    hom = InfrastructureManager(GeneratorConfig(heterogeneous=False)).instantiate_infrastructure(20, seed=3)
    assert het[2] == hom[2]  # same links
    for n in het[0]:
        for k in ("throughput_cap", "energy", "proc_delay"):
            assert het[1][n][k] == hom[1][n][k]
        assert hom[1][n]["mtbf"] == 2000


def test_json_roundtrip(tmp_path):
    im = InfrastructureManager()
    inst = im.instantiate_infrastructure(15, seed=2)
    path = tmp_path / "inst.json"
    im.export_json(path)
    im2 = InfrastructureManager()
    assert im2.load_json(path) == inst


# ---------------------------------------------------------------------- #
# Validator (independent of the solver)
# ---------------------------------------------------------------------- #
def _toy():
    kb = KnowledgeBase()
    nodes, caps, comm = InfrastructureManager().instantiate_infrastructure(10, seed=0)
    return kb, nodes, caps, comm, kb.default_system_nfrs


def test_validator_flags_privacy_and_capacity():
    kb, nodes, caps, comm, nfrs = _toy()
    cloud = [n for n in nodes if caps[n]["tier"] == "Cloud"][0]
    edge = [n for n in nodes if caps[n]["tier"] == "Edge"][0]
    # Everything on one Edge node: capacity violated; nothing on the cloud.
    v = ValidationManager(kb).verify_deployment({c: [edge] for c in kb.components}, nodes, caps, comm, nfrs)
    assert any(f == "capacity" for f, _ in v)
    # A high-privacy service on the cloud violates privacy.
    asg = {c: [edge] for c in kb.components}
    asg["DetectSmoke"] = [cloud]
    v = ValidationManager(kb).verify_deployment(asg, nodes, caps, comm, nfrs)
    assert any(f == "privacy" and "DetectSmoke" in m for f, m in v)


def test_bandwidth_requirement_is_rounded_up():
    kb, *_ = _toy()
    old = kb.bandwidth_per_job
    try:
        kb.bandwidth_per_job = 0.1
        assert kb.required_bandwidth({"performance": {"min_throughput": 30}}) == 3   # 3.0000000000000004
        kb.bandwidth_per_job = 0.085
        assert kb.required_bandwidth({"performance": {"min_throughput": 30}}) == 3   # 2.55 -> 3, not 2
    finally:
        kb.bandwidth_per_job = old


def test_validator_checks_colocated_hop_latency():
    kb, nodes, caps, comm, nfrs = _toy()
    (c1, c2), sla = next(iter(kb.latency_constraints.items()))
    n = nodes[0]
    caps = {k: dict(v) for k, v in caps.items()}
    caps[n]["proc_delay"] = sla  # co-located hop costs 2 * proc_delay > SLA
    asg = {c: [n] for c in kb.components}
    v = ValidationManager(kb).verify_deployment(asg, nodes, caps, comm, nfrs)
    assert any(f == "hop_latency" and c1 in m and c2 in m for f, m in v)


def test_validator_flags_missing_service():
    kb, nodes, caps, comm, nfrs = _toy()
    v = ValidationManager(kb).verify_deployment({}, nodes, caps, comm, nfrs)
    assert v and all(f == "placement" for f, _ in v)


# ---------------------------------------------------------------------- #
# Solver-based tests
# ---------------------------------------------------------------------- #
@needs_solver
@pytest.mark.parametrize("objective", OBJECTIVES)
def test_objective_value_matches_independent_metrics(objective):
    from ui.user_interface import UserInterface
    ui = UserInterface(verbose=False, time_limit=60)
    ui.setup(10, seed=0)
    res, violations = ui.solve(objective, report=False)
    assert res.ok and not violations
    assert res.objective_value == pytest.approx(res.metrics[objective])
    assert res.best_bound <= res.objective_value + 1e-6


@needs_solver
def test_min_energy_not_worse_than_feasible():
    from ui.user_interface import UserInterface
    ui = UserInterface(verbose=False, time_limit=60)
    ui.setup(20, seed=1)
    f, _ = ui.solve("feasible", report=False)
    m, _ = ui.solve("energy", report=False)
    assert m.energy <= f.energy


@needs_solver
def test_diagnosis_of_infeasible_instance():
    from ui.user_interface import UserInterface
    ui = UserInterface(verbose=False, time_limit=60)
    ui.setup(10, seed=3)          # 10-node instance that cannot host all services
    res, _ = ui.solve("feasible", report=False)
    assert not res.ok
    diag = ui.diagnose()
    assert not diag["feasible"] and diag["conflict"]
    # relaxing one reported family restores feasibility
    fam = diag["relaxations"][0]
    from constraints.constraint_manager import FAMILIES
    r2, _ = ui.solve("feasible", enabled_families=[f for f in FAMILIES if f != fam], report=False)
    assert r2.ok


@needs_solver
def test_diagnosis_reports_time_out_instead_of_conflict():
    from ortools.sat.python import cp_model
    from ui.user_interface import UserInterface

    class TimeOut:  # a solver that always hits the time limit
        def Solve(self, model):
            return cp_model.UNKNOWN

    ui = UserInterface(verbose=False, time_limit=60)
    ui.setup(10, seed=3)
    ui.solution_manager._make_solver = lambda *a, **k: TimeOut()
    diag = ui.diagnose()
    assert diag["feasible"] is None and not diag["conflict"] and not diag["relaxations"]
    assert "time limit" in ui.reporting_manager.diagnosis(diag)


@needs_solver
def test_ablated_deployment_is_rechecked_against_full_requirements():
    from ui.user_interface import UserInterface
    from constraints.constraint_manager import FAMILIES
    ui = UserInterface(verbose=False, time_limit=60)
    ui.setup(10, seed=0)
    res, violations = ui.solve("energy", enabled_families=[f for f in FAMILIES if f != "privacy"],
                               report=False)
    assert res.ok
    assert any(f == "privacy" for f, _ in violations)
    full, v_full = ui.solve("energy", report=False)
    assert not v_full and res.energy <= full.energy
