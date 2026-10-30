"""
Node Manager: instantiates infrastructure nodes with their capacities and
characteristics.

Creates Edge, Fog, and Cloud nodes with:
- CPU and memory capacities
- Throughput capacity
- Energy cost
- Processing delay
- MTBF (Mean Time Between Failures)
- Encryption-compliance level
- Privacy capability
- Cost per allocated vCPU-hour and grid carbon intensity (illustrative)

All values are drawn from the ranges in ``GeneratorConfig`` using seeded
pseudo-random generators, so every instance can be regenerated exactly.
"""

import random

from .generator_config import GeneratorConfig, EXT_SEED_OFFSET


class NodeManager:
    """
    Instantiates the infrastructure node set, including per-node capacities,
    energy costs, processing delays, MTBF, encryption levels, and privacy levels.
    """

    def __init__(self, config=None):
        self.config = config or GeneratorConfig()
        self.nodes = []
        self.capabilities = {}

    def tier_counts(self, num_nodes):
        """Number of Edge, Fog and Cloud nodes for a given infrastructure size."""
        edge_count = int(num_nodes * self.config.edge_share)
        fog_count = int(num_nodes * self.config.fog_share)
        cloud_count = num_nodes - edge_count - fog_count
        return edge_count, fog_count, cloud_count

    def instantiate_nodes(self, num_nodes, core_rng=None, ext_rng=None, seed=None):
        """
        Generate Edge/Fog/Cloud nodes.

        Args:
            num_nodes: total number of nodes
            core_rng: random.Random for the original attributes (optional)
            ext_rng: random.Random for the extended attributes (optional)
            seed: used to create the generators when they are not given

        Returns:
            tuple: (nodes list, capabilities dict)
        """
        if core_rng is None:
            core_rng = random.Random(seed)
        if ext_rng is None:
            ext_rng = random.Random(None if seed is None else seed + EXT_SEED_OFFSET)

        counts = dict(zip(("Edge", "Fog", "Cloud"), self.tier_counts(num_nodes)))
        self.nodes = []
        self.capabilities = {}

        for tier in ("Edge", "Fog", "Cloud"):
            prof = self.config.tiers[tier]
            for i in range(counts[tier]):
                nd = f"{tier}Node{i}"
                self.nodes.append(nd)
                # Core attributes (same draw order as the original generator)
                cap = {
                    "tier": tier,
                    "cpu": prof.cpu,
                    "memory": prof.memory,
                    "throughput_cap": core_rng.randint(*prof.throughput_cap),
                    "energy": core_rng.randint(*prof.energy),
                    "proc_delay": core_rng.randint(*prof.proc_delay),
                    "privacy_capability": prof.privacy_capability,
                }
                # Extended attributes (separate stream)
                mtbf = ext_rng.randint(*prof.mtbf)
                enc = ext_rng.randint(*prof.encryption_compliance)
                cap["cost_per_vcpu"] = ext_rng.randint(*prof.cost_per_vcpu)
                cap["carbon_intensity"] = ext_rng.randint(*prof.carbon_intensity)
                if self.config.heterogeneous:
                    cap["mtbf"] = mtbf
                    cap["encryption_compliance"] = enc
                else:
                    cap["mtbf"] = prof.legacy_mtbf
                    cap["encryption_compliance"] = prof.legacy_encryption
                # Carbon emitted if the node is used: energy x intensity (scaled to integers)
                cap["carbon"] = round(cap["energy"] * cap["carbon_intensity"] / 100)
                self.capabilities[nd] = cap

        return self.nodes, self.capabilities

    @staticmethod
    def get_node_type(node):
        """Return the tier of a node: "Edge", "Fog", "Cloud", or "Unknown"."""
        if node.startswith("EdgeNode"):
            return "Edge"
        if node.startswith("FogNode"):
            return "Fog"
        if node.startswith("CloudNode"):
            return "Cloud"
        return "Unknown"

    def get_node_capability(self, node, capability):
        """Get a specific capability of a node (None if unknown)."""
        return self.capabilities.get(node, {}).get(capability)
