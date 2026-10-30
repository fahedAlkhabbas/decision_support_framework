"""
Model Manager: initialises the optimisation model and its decision variables.

Responsible for:
- creating the CP-SAT model
- defining the binary placement variables x[c, n]
- defining the binary node-usage variables u[n]
- bundling the model, its variables and the problem data in a DeploymentModel
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ortools.sat.python import cp_model


@dataclass
class DeploymentModel:
    """A CP-SAT model together with its variables and problem data."""
    model: cp_model.CpModel
    A: Dict                      # (component, node) -> BoolVar  (x_{c,n})
    nodes: List[str]
    components: List[str]
    caps: Dict
    comm: Dict
    system_nfrs: Dict
    used: Dict = field(default_factory=dict)          # node -> BoolVar  (u_n)
    hop_vars: Dict = field(default_factory=dict)      # (flow, c, d, n1, n2) -> BoolVar (y)
    flow_delay: Dict = field(default_factory=dict)    # flow -> linear expression (ms)
    enabled_families: frozenset = frozenset()
    family_literals: Dict = field(default_factory=dict)  # family -> BoolVar (diagnostics mode)
    eligible: Dict = field(default_factory=dict)      # component -> nodes not statically excluded
    replicas: int = 1
    objective_name: Optional[str] = None

    def stats(self):
        """Size of the model (after encoding, before presolve)."""
        proto = self.model.Proto() if hasattr(self.model, "Proto") else self.model.proto
        return {
            "variables": len(proto.variables),
            "constraints": len(proto.constraints),
            "placement_vars": len(self.A),
            "hop_vars": len(self.hop_vars),
        }


class ModelManager:
    """
    Instantiates a solver-ready optimisation model from the scenario, the
    infrastructure, and the microservice catalogue.
    """

    def __init__(self, knowledge_base, component_catalog_manager):
        self.kb = knowledge_base
        self.comp_catalog = component_catalog_manager

    def initialize_model(self, nodes, components):
        """
        Create a CP-SAT model with one Boolean variable x[c, n] per
        (component, node) pair: x[c, n] = 1 iff component c is deployed on node n.

        Returns:
            tuple: (model, variables dict)
        """
        model = cp_model.CpModel()
        A = {
            (c, n): model.NewBoolVar(f"x[{c},{n}]")
            for c in components
            for n in nodes
        }
        return model, A

    def create_deployment_model(self, nodes, components, caps, comm, system_nfrs):
        """Create a DeploymentModel with placement and node-usage variables."""
        model, A = self.initialize_model(nodes, components)
        dm = DeploymentModel(
            model=model, A=A, nodes=list(nodes), components=list(components),
            caps=caps, comm=comm, system_nfrs=system_nfrs,
        )
        for n in nodes:
            u = model.NewBoolVar(f"u[{n}]")
            # u_n = max_c x[c, n]: a node is used iff it hosts at least one service
            model.AddMaxEquality(u, [A[c, n] for c in components])
            dm.used[n] = u
        return dm
