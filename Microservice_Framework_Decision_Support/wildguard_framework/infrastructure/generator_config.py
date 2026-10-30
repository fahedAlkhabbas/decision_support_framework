"""
Generator configuration for the synthetic Edge-Fog-Cloud infrastructures used
in the experiments.

Every value used to generate an infrastructure is defined here so that the
experiments can be reproduced exactly. Integer ranges are inclusive and are
sampled uniformly (``random.Random.randint``).

Two independent pseudo-random streams are used, both derived from the instance
seed:
  * the *core* stream (seed) draws the attributes of the original generator
    (throughput capacity, energy cost, processing delay) and the links;
  * the *extended* stream (seed + EXT_SEED_OFFSET) draws the attributes added
    in the revision (MTBF, encryption compliance, cost, carbon intensity).
Hence, enabling or disabling the extended attributes does not change the core
attributes or the topology of an instance with a given seed.
"""

from dataclasses import dataclass, field
from typing import Dict, Tuple

EXT_SEED_OFFSET = 1_000_003


@dataclass(frozen=True)
class TierProfile:
    cpu: int                         # vCPU
    memory: int                      # GB
    throughput_cap: Tuple[int, int]  # events/s
    energy: Tuple[int, int]          # energy units per used node
    proc_delay: Tuple[int, int]      # ms per processed event
    privacy_capability: str
    # Extended (heterogeneous) attributes
    mtbf: Tuple[int, int]                  # hours
    encryption_compliance: Tuple[int, int]  # compliance level (0-100)
    cost_per_vcpu: Tuple[int, int]         # cost units per allocated vCPU-hour (illustrative)
    carbon_intensity: Tuple[int, int]      # gCO2e/kWh of the node's grid (illustrative)
    # Values used by the original (homogeneous) generator
    legacy_mtbf: int = 2000
    legacy_encryption: int = 96


@dataclass(frozen=True)
class GeneratorConfig:
    # Share of nodes per tier (cloud gets the remainder)
    edge_share: float = 0.6
    fog_share: float = 0.3
    # If False, MTBF/encryption are the original homogeneous values
    heterogeneous: bool = True
    tiers: Dict[str, TierProfile] = field(default_factory=lambda: {
        "Edge": TierProfile(
            cpu=4, memory=8, throughput_cap=(50, 120), energy=(25, 45), proc_delay=(2, 10),
            privacy_capability="high",
            mtbf=(400, 2500), encryption_compliance=(96, 99),
            cost_per_vcpu=(1, 5), carbon_intensity=(50, 400),
            legacy_mtbf=2000, legacy_encryption=96,
        ),
        "Fog": TierProfile(
            cpu=16, memory=64, throughput_cap=(300, 500), energy=(180, 250), proc_delay=(10, 20),
            privacy_capability="intermediate",
            mtbf=(1000, 3000), encryption_compliance=(95, 99),
            cost_per_vcpu=(10, 30), carbon_intensity=(50, 400),
            legacy_mtbf=2000, legacy_encryption=98,
        ),
        "Cloud": TierProfile(
            cpu=64, memory=256, throughput_cap=(800, 1000), energy=(600, 1100), proc_delay=(2, 10),
            privacy_capability="low",
            mtbf=(1500, 5000), encryption_compliance=(97, 99),
            cost_per_vcpu=(20, 60), carbon_intensity=(20, 700),
            legacy_mtbf=2000, legacy_encryption=99,
        ),
    })
    # Link latency ranges (ms) per tier pair
    latency: Dict[Tuple[str, str], Tuple[int, int]] = field(default_factory=lambda: {
        ("Edge", "Edge"): (2, 10),
        ("Fog", "Fog"): (10, 20),
        ("Cloud", "Cloud"): (2, 10),
        ("Edge", "Fog"): (15, 30),
        ("Cloud", "Fog"): (60, 120),
        ("Cloud", "Edge"): (70, 150),
    })
    # Link bandwidth ranges (Mbps) per tier pair
    bandwidth: Dict[Tuple[str, str], Tuple[int, int]] = field(default_factory=lambda: {
        ("Edge", "Edge"): (20, 80),
        ("Edge", "Fog"): (50, 200),
        ("Fog", "Fog"): (200, 600),
        ("Cloud", "Fog"): (100, 400),
        ("Cloud", "Cloud"): (500, 1000),
        ("Cloud", "Edge"): (20, 100),
    })
    # Guaranteed connectivity
    edge_to_fog_links: int = 3     # each Edge node is linked to (up to) 3 random Fog nodes
    fog_to_cloud_links: int = 2    # each Fog node is linked to (up to) 2 random Cloud nodes
    # Probability of an additional link between two not-yet-linked nodes
    extra_link_prob: Dict[Tuple[str, str], float] = field(default_factory=lambda: {
        ("Edge", "Edge"): 0.7,
        ("Fog", "Fog"): 0.7,
        ("Cloud", "Cloud"): 0.7,
        ("Edge", "Fog"): 0.8,
        ("Cloud", "Fog"): 0.6,
        ("Cloud", "Edge"): 0.4,
    })

    @staticmethod
    def pair(tA, tB):
        """Canonical (sorted) key for a tier pair."""
        return tuple(sorted((tA, tB)))

    def describe(self):
        """Plain dictionary of the configuration (for logging into results)."""
        return {
            "edge_share": self.edge_share,
            "fog_share": self.fog_share,
            "heterogeneous": self.heterogeneous,
            "tiers": {k: vars(v) for k, v in self.tiers.items()},
            "latency": {"-".join(k): v for k, v in self.latency.items()},
            "bandwidth": {"-".join(k): v for k, v in self.bandwidth.items()},
            "edge_to_fog_links": self.edge_to_fog_links,
            "fog_to_cloud_links": self.fog_to_cloud_links,
            "extra_link_prob": {"-".join(k): v for k, v in self.extra_link_prob.items()},
        }
