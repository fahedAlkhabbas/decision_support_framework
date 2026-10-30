"""
Knowledge Base: stores scenario knowledge (microservices, requirements, data
flows, hop-wise SLAs, privacy compatibility, configuration parameters) and the
history of generated deployments.

Scenario-specific knowledge is loaded from a JSON scenario file (by default
``scenarios/wildfire_intelguard.json``). The optimisation model is generic: to
apply the framework to another system, provide another scenario file with the
same schema.
"""

import math
import json
import os

_DEFAULT_SCENARIO = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "scenarios",
    "wildfire_intelguard.json",
)


class KnowledgeBase:
    """
    Maintains knowledge about the infrastructure, microservices, constraints,
    trade-off analyses, and historical deployments.
    """

    def __init__(self, scenario_path=None):
        """Load the scenario (Wildfire-IntelGuard by default)."""
        self.scenario_path = scenario_path or _DEFAULT_SCENARIO
        with open(self.scenario_path, "r", encoding="utf-8") as fh:
            spec = json.load(fh)
        self.load_scenario(spec)
        # History of generated deployments (appended by the user interface).
        self.deployment_history = []

    # ------------------------------------------------------------------ #
    # Scenario loading
    # ------------------------------------------------------------------ #
    def load_scenario(self, spec):
        """Populate the knowledge base from a scenario dictionary."""
        self.scenario_name = spec.get("name", "unnamed")
        self.default_system_nfrs = spec.get("system_nfrs", {})
        self.replication_policy = sorted(
            spec.get("replication_policy", []),
            key=lambda r: r["min_availability"],
        )
        self.bandwidth_per_job = spec.get("bandwidth_per_job", 0.1)  # Mbps per event/s
        self.privacy_compatibility = spec["privacy_compatibility"]

        self.comp_requirements = {k: dict(v) for k, v in spec["components"].items()}
        self.components = list(self.comp_requirements.keys())

        self.dataflow_paths = {k: list(v) for k, v in spec["dataflows"].items()}

        self.latency_constraints = {
            (e["from"], e["to"]): e["max_ms"] for e in spec.get("latency_constraints", [])
        }

    # ------------------------------------------------------------------ #
    # Accessors
    # ------------------------------------------------------------------ #
    def get_component_requirements(self, component):
        """Get requirements for a specific component."""
        return self.comp_requirements.get(component, {})

    def get_dataflow(self, flow_name):
        """Get a specific data-flow chain."""
        return self.dataflow_paths.get(flow_name, [])

    def get_latency_constraint(self, component1, component2):
        """Get the hop latency SLA between two components (ms), if any."""
        return self.latency_constraints.get((component1, component2), None)

    def get_privacy_compatibility(self, privacy_level):
        """Get the node privacy levels compatible with a service privacy level."""
        return self.privacy_compatibility.get(privacy_level, [])

    def replicas_for(self, availability):
        """Number of replicas required by the replication policy for a given
        system availability target (1 if no rule applies)."""
        rep = 1
        for rule in self.replication_policy:
            if availability >= rule["min_availability"]:
                rep = rule["replicas"]
        return rep

    def flow_hops(self):
        """All (flow, upstream, downstream) hops of all data flows."""
        hops = []
        for fname, chain in self.dataflow_paths.items():
            for c1, c2 in zip(chain, chain[1:]):
                hops.append((fname, c1, c2))
        return hops

    def required_bandwidth(self, system_nfrs):
        """Bandwidth (Mbps) each inter-node hop must offer."""
        # Rounded UP to whole Mbps (the original prototype truncated with int(),
        # which under-estimates fractional requirements). The small tolerance
        # absorbs floating-point noise, e.g., 30 * 0.1 = 3.0000000000000004 -> 3.
        bw = system_nfrs["performance"]["min_throughput"] * self.bandwidth_per_job
        return int(math.ceil(bw - 1e-9))

    def record_deployment(self, record):
        """Store a generated deployment (dict) in the deployment history."""
        self.deployment_history.append(record)
