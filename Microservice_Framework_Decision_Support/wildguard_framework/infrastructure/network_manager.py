"""
Network Manager: generates communication links between nodes and specifies
their latency and bandwidth.

Connectivity guarantees:
- each Edge node is linked to (up to) 3 randomly chosen Fog nodes;
- each Fog node is linked to (up to) 2 randomly chosen Cloud nodes;
- every other node pair is linked with a tier-dependent probability.
Links are bidirectional and symmetric. All ranges and probabilities are in
``GeneratorConfig``.
"""

import random

from .node_manager import NodeManager
from .generator_config import GeneratorConfig


class NetworkManager:
    """Generates the links between nodes and specifies their latency and bandwidth."""

    def __init__(self, node_manager=None, config=None):
        self.config = config or (node_manager.config if node_manager else GeneratorConfig())
        self.node_manager = node_manager or NodeManager(self.config)
        self.communication_links = {}

    def generate_links(self, nodes, capabilities, rng=None):
        """
        Generate communication links with tier-based latency and bandwidth.

        Args:
            nodes: list of node names
            capabilities: dict of node capabilities (unused, kept for API stability)
            rng: random.Random instance (core stream)

        Returns:
            dict: {(a, b): {"latency": ms, "bandwidth": Mbps}} for both directions
        """
        rng = rng or random.Random()
        cfg = self.config
        self.communication_links = {}
        edge_nodes = [n for n in nodes if n.startswith("EdgeNode")]
        fog_nodes = [n for n in nodes if n.startswith("FogNode")]
        cloud_nodes = [n for n in nodes if n.startswith("CloudNode")]
        tier = self.node_manager.get_node_type

        def add_link(a, b):
            key = cfg.pair(tier(a), tier(b))
            lat = rng.randint(*cfg.latency[key])
            bw = rng.randint(*cfg.bandwidth[key])
            self.communication_links[(a, b)] = {"latency": lat, "bandwidth": bw}
            self.communication_links[(b, a)] = self.communication_links[(a, b)]

        for e in edge_nodes:
            k = min(cfg.edge_to_fog_links, len(fog_nodes))
            for f in rng.sample(fog_nodes, k):
                add_link(e, f)

        for f in fog_nodes:
            k = min(cfg.fog_to_cloud_links, len(cloud_nodes))
            for c in rng.sample(cloud_nodes, k):
                add_link(f, c)

        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                a, b = nodes[i], nodes[j]
                if (a, b) in self.communication_links:
                    continue
                p = cfg.extra_link_prob[cfg.pair(tier(a), tier(b))]
                if rng.random() <= p:
                    add_link(a, b)

        return self.communication_links

    def get_link_properties(self, node1, node2):
        """Latency and bandwidth of the link between two nodes ({} if none)."""
        return self.communication_links.get((node1, node2), {})
