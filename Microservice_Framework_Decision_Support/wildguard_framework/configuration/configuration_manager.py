"""
Configuration Manager: validates and normalises the architects' input.

Responsible for:
- Validating system-level and component-level specifications
- Transforming data flows to ordered chains
- Normalizing specifications to standard format
- Raising clear and actionable validation errors
"""


class ConfigurationManager:
    """
    Responsible for transforming the specifications provided by the architect
    into validated and normalized configurations used by other components.
    Transforms data flows between microservices to ordered chains and
    per-hop Service-Level Agreements (SLAs).
    """

    def __init__(self, knowledge_base):
        """
        Initialize the configuration manager.

        Args:
            knowledge_base: KnowledgeBase instance
        """
        self.kb = knowledge_base

    def validate_user_input(self, system_nfrs, dataflow_paths, latency_constraints):
        """
        Validates the architects' input and raises clear, actionable errors
        when it is incomplete or inconsistent.

        Args:
            system_nfrs: System-level non-functional requirements
            dataflow_paths: Data flow chains
            latency_constraints: Hop-wise latency constraints

        Returns:
            bool: True if all inputs are valid

        Raises:
            ValueError: If validation fails with descriptive error message
        """
        # Validate system NFRs
        if "availability" not in system_nfrs:
            raise ValueError("System NFR 'availability' is required")
        if "performance" not in system_nfrs:
            raise ValueError("System NFR 'performance' is required")
        if "security" not in system_nfrs:
            raise ValueError("System NFR 'security' is required")

        # Validate performance requirements
        perf = system_nfrs["performance"]
        if "max_delay" not in perf:
            raise ValueError("Performance NFR 'max_delay' is required")
        if "min_throughput" not in perf:
            raise ValueError("Performance NFR 'min_throughput' is required")

        # Validate dataflow paths
        for flow_name, chain in dataflow_paths.items():
            if not isinstance(chain, list) or len(chain) < 2:
                raise ValueError(f"Dataflow '{flow_name}' must have at least 2 components")
            for comp in chain:
                if comp not in self.kb.components:
                    raise ValueError(f"Component '{comp}' in flow '{flow_name}' not found")

        # Validate latency constraints
        for (c1, c2), lat in latency_constraints.items():
            if c1 not in self.kb.components or c2 not in self.kb.components:
                raise ValueError(
                    f"Latency constraint references unknown components: {c1}, {c2}"
                )
            if lat <= 0:
                raise ValueError(
                    f"Latency constraint for ({c1}, {c2}) must be positive"
                )

        return True

    def normalize_specifications(self, system_nfrs):
        """
        Normalizes specifications to standard format.

        Args:
            system_nfrs: System-level non-functional requirements

        Returns:
            dict: Normalized specifications
        """
        # Ensure all required fields are present
        normalized = {
            "availability": system_nfrs.get("availability", 99.0),
            "performance": {
                "max_delay": system_nfrs.get("performance", {}).get("max_delay", 5000),
                "min_throughput": system_nfrs.get("performance", {}).get("min_throughput", 30),
            },
            "security": system_nfrs.get("security", 90),
        }
        return normalized

    def validate_dataflow_chain(self, chain):
        """
        Validates a single dataflow chain.

        Args:
            chain: List of component names in the chain

        Returns:
            bool: True if chain is valid

        Raises:
            ValueError: If chain is invalid
        """
        if not isinstance(chain, list) or len(chain) < 2:
            raise ValueError("Dataflow chain must have at least 2 components")
        for comp in chain:
            if comp not in self.kb.components:
                raise ValueError(f"Component '{comp}' not found in catalog")
        return True

    def validate_nfr_values(self, system_nfrs):
        """
        Validates that NFR values are within reasonable ranges.

        Args:
            system_nfrs: System-level non-functional requirements

        Returns:
            bool: True if all values are valid

        Raises:
            ValueError: If any value is out of range
        """
        # Validate availability (0-100)
        avail = system_nfrs.get("availability", 99.0)
        if not (0 <= avail <= 100):
            raise ValueError(f"Availability must be between 0 and 100, got {avail}")

        # Validate security (0-100)
        security = system_nfrs.get("security", 90)
        if not (0 <= security <= 100):
            raise ValueError(f"Security must be between 0 and 100, got {security}")

        # Validate performance
        perf = system_nfrs.get("performance", {})
        max_delay = perf.get("max_delay", 5000)
        if max_delay <= 0:
            raise ValueError(f"Max delay must be positive, got {max_delay}")

        min_throughput = perf.get("min_throughput", 30)
        if min_throughput <= 0:
            raise ValueError(f"Min throughput must be positive, got {min_throughput}")

        return True
