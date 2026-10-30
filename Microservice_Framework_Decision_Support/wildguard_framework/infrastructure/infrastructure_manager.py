"""
Infrastructure Manager: orchestrates node and network management.

Responsible for:
- instantiating the complete (seeded) infrastructure graph
- managing both node and network components
- exporting/importing an infrastructure instance as JSON for reproducibility
"""

import json
import random

from .node_manager import NodeManager
from .network_manager import NetworkManager
from .generator_config import GeneratorConfig, EXT_SEED_OFFSET


class InfrastructureManager:
    """
    Models and instantiates the infrastructure that will host the
    microservices. Comprises the Node Manager and the Network Manager.
    """

    def __init__(self, config=None):
        self.config = config or GeneratorConfig()
        self.node_manager = NodeManager(self.config)
        self.network_manager = NetworkManager(self.node_manager, self.config)
        self.nodes = []
        self.capabilities = {}
        self.communication_links = {}
        self.seed = None

    def instantiate_infrastructure(self, num_nodes, seed=None):
        """
        Instantiate the complete infrastructure graph.

        Args:
            num_nodes: total number of nodes
            seed: instance seed (None = non-reproducible)

        Returns:
            tuple: (nodes list, capabilities dict, communication links dict)
        """
        self.seed = seed
        core_rng = random.Random(seed)
        ext_rng = random.Random(None if seed is None else seed + EXT_SEED_OFFSET)
        self.nodes, self.capabilities = self.node_manager.instantiate_nodes(
            num_nodes, core_rng=core_rng, ext_rng=ext_rng
        )
        self.communication_links = self.network_manager.generate_links(
            self.nodes, self.capabilities, rng=core_rng
        )
        return self.nodes, self.capabilities, self.communication_links

    def export_json(self, path):
        """Write the current instance (nodes, capabilities, links) to a JSON file."""
        links = [
            {"a": a, "b": b, **props}
            for (a, b), props in self.communication_links.items()
            if a < b
        ]
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(
                {"seed": self.seed, "nodes": self.nodes,
                 "capabilities": self.capabilities, "links": links},
                fh, indent=1,
            )

    def load_json(self, path):
        """Load an instance previously written with ``export_json``."""
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        self.seed = data.get("seed")
        self.nodes = data["nodes"]
        self.capabilities = data["capabilities"]
        self.communication_links = {}
        for l in data["links"]:
            props = {"latency": l["latency"], "bandwidth": l["bandwidth"]}
            self.communication_links[(l["a"], l["b"])] = props
            self.communication_links[(l["b"], l["a"])] = props
        self.node_manager.nodes, self.node_manager.capabilities = self.nodes, self.capabilities
        self.network_manager.communication_links = self.communication_links
        return self.nodes, self.capabilities, self.communication_links

    def get_node_type(self, node):
        """Tier of a node (Edge, Fog, Cloud, or Unknown)."""
        return self.node_manager.get_node_type(node)

    def get_node_capability(self, node, capability):
        """A specific capability of a node."""
        return self.node_manager.get_node_capability(node, capability)

    def get_link_properties(self, node1, node2):
        """Latency and bandwidth of a communication link."""
        return self.network_manager.get_link_properties(node1, node2)

    def get_node_count_by_tier(self):
        """Count of nodes per tier."""
        return {
            "Edge": sum(1 for n in self.nodes if n.startswith("EdgeNode")),
            "Fog": sum(1 for n in self.nodes if n.startswith("FogNode")),
            "Cloud": sum(1 for n in self.nodes if n.startswith("CloudNode")),
        }

    def link_count(self):
        """Number of undirected links."""
        return len(self.communication_links) // 2
