"""
User Interface: orchestrates the framework components.

Implements the deployment-generation process of the paper:
 1. problem setup
 2. validate user input
 3. instantiate the infrastructure (seeded)
 4. register microservices in the catalogue
 5. initialise the optimisation model
 6. encode constraints
 7. solve and optimise
 8. verify topologies (independent re-check of every requirement)
 9. report (and explain) topologies; store them in the knowledge base
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.knowledge_base import KnowledgeBase
from components.component_catalog import ComponentCatalogManager
from infrastructure.infrastructure_manager import InfrastructureManager
from configuration.configuration_manager import ConfigurationManager
from models.model_manager import ModelManager
from constraints.constraint_manager import ConstraintManager, FAMILIES
from solution.solution_manager import SolutionManager
from solution.multi_objective import MultiObjectiveOptimizer
from validation.validation_manager import ValidationManager
from reporting.reporting_manager import ReportingManager


class UserInterface:
    """
    Front end through which architects specify microservices, requirements,
    data flows and infrastructure, and obtain (explained) deployment
    recommendations.
    """

    def __init__(self, scenario_path=None, generator_config=None, time_limit=30.0,
                 workers=None, solver_seed=0, verbose=True):
        self.kb = KnowledgeBase(scenario_path)
        self.comp_catalog = ComponentCatalogManager(self.kb)
        self.config_manager = ConfigurationManager(self.kb)
        self.infra_manager = InfrastructureManager(generator_config)
        self.model_manager = ModelManager(self.kb, self.comp_catalog)
        self.constraint_manager = ConstraintManager(self.kb)
        self.solution_manager = SolutionManager(self.kb, time_limit, workers, solver_seed)
        self.validation_manager = ValidationManager(self.kb)
        self.reporting_manager = ReportingManager(verbose)
        self.verbose = verbose
        self.nodes, self.caps, self.comm = [], {}, {}
        self.system_nfrs = None

    # ------------------------------------------------------------------ #
    # Steps 1-4
    # ------------------------------------------------------------------ #
    def setup(self, num_nodes, system_nfrs=None, seed=None, infrastructure_file=None):
        """Validate the input and instantiate the infrastructure."""
        system_nfrs = system_nfrs or self.kb.default_system_nfrs
        self.config_manager.validate_user_input(
            system_nfrs, self.kb.dataflow_paths, self.kb.latency_constraints)
        self.config_manager.validate_nfr_values(system_nfrs)
        self.system_nfrs = system_nfrs
        if infrastructure_file:
            self.nodes, self.caps, self.comm = self.infra_manager.load_json(infrastructure_file)
        else:
            self.nodes, self.caps, self.comm = self.infra_manager.instantiate_infrastructure(
                num_nodes, seed=seed)
        self.comp_catalog.validate_and_register_microservices(self.kb.components)
        return self.nodes, self.caps, self.comm

    # ------------------------------------------------------------------ #
    # Steps 5-6
    # ------------------------------------------------------------------ #
    def build_model(self, enabled_families=None, diagnostics=False):
        """Fresh DeploymentModel for the current infrastructure."""
        dm = self.model_manager.create_deployment_model(
            self.nodes, self.kb.components, self.caps, self.comm, self.system_nfrs)
        return self.constraint_manager.encode_constraints(dm, enabled_families, diagnostics)

    # ------------------------------------------------------------------ #
    # Steps 7-9
    # ------------------------------------------------------------------ #
    def solve(self, objective="feasible", sense="min", enabled_families=None,
              time_limit=None, report=True):
        """Build, solve, validate and report. Returns (SolveResult, violations)."""
        dm = self.build_model(enabled_families)
        res = self.solution_manager.solve(dm, objective, sense=sense, time_limit=time_limit)
        valid, msg, violations = self.validation_manager.verify_topologies(
            res, self.nodes, self.caps, self.comm, self.system_nfrs)
        if report:
            self.reporting_manager.report_topologies(res, valid, msg)
        if res.ok:
            self.kb.record_deployment({
                "seed": self.infra_manager.seed, "nodes": len(self.nodes),
                "objective": res.objective, "sense": sense, "valid": valid,
                "summary": res.summary(), "assignment": res.assignment,
            })
        return res, violations

    def diagnose(self, enabled_families=None, time_limit=None):
        """Explain why no deployment exists (minimal conflicting families)."""
        fams = list(enabled_families or FAMILIES)
        return self.solution_manager.diagnose_infeasibility(
            lambda f, d: self.build_model(f, d), fams, time_limit)

    def multi_objective(self, enabled_families=None):
        """MultiObjectiveOptimizer bound to the current infrastructure."""
        return MultiObjectiveOptimizer(
            lambda: self.build_model(enabled_families), self.kb, self.solution_manager)

    def explain(self, result, title="Deployment"):
        return self.reporting_manager.explain(
            self.kb, self.constraint_manager, self.nodes, self.caps, self.comm,
            self.system_nfrs, result, title)

    # ------------------------------------------------------------------ #
    # Backward-compatible entry point (v1)
    # ------------------------------------------------------------------ #
    def run_deployment_scenario(self, num_nodes, system_nfrs=None, objective="feasible",
                                seed=None, time_limit=None):
        """
        Full process on a fresh infrastructure.

        objective: "feasible", "minimize"/"maximize" (energy), or any objective name.
        Returns: (ok, time_taken, energy, used_nodes)
        """
        if self.verbose:
            print(f"\n*** Testing on {num_nodes} nodes (seed={seed}) ***")
        self.setup(num_nodes, system_nfrs, seed)
        res, violations = self.solve(objective, time_limit=time_limit)
        ok = res.ok and not violations
        return ok, res.time_s, res.energy, res.used_nodes

    # accessors
    def get_knowledge_base(self):
        return self.kb

    def get_infrastructure_manager(self):
        return self.infra_manager

    def get_reporting_manager(self):
        return self.reporting_manager
