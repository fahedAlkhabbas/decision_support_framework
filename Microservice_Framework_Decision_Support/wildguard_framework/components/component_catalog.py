"""
Component Catalog Manager: Manages microservices registry and validation.

Responsible for:
- Validating and registering microservices in a versioned catalog
- Providing access to component requirements
- Supporting reuse of microservices across different scenarios
"""


class ComponentCatalogManager:


    def __init__(self, knowledge_base):
        """
        Initialize the component catalog manager.

        Args:
            knowledge_base: KnowledgeBase instance containing component definitions
        """
        self.kb = knowledge_base

    def validate_and_register_microservices(self, components):
        """
        Validates and registers microservices in a versioned service catalog registry.

        Args:
            components: List of component names to validate

        Returns:
            bool: True if all components are valid

        Raises:
            ValueError: If any component is not found in knowledge base
        """
        for comp in components:
            if comp not in self.kb.comp_requirements:
                raise ValueError(f"Microservice {comp} not found in knowledge base")
        return True

    def get_component_requirements(self, component):
        """
        Returns requirements for a specific component.

        Args:
            component: Component name

        Returns:
            dict: Component requirements (cpu, memory, response_time, etc.)
        """
        return self.kb.comp_requirements.get(component, {})

    def get_all_components(self):
        """
        Returns all registered components.

        Returns:
            list: All component names
        """
        return self.kb.components

    def get_component_count(self):
        """
        Get the total number of registered components.

        Returns:
            int: Number of components
        """
        return len(self.kb.components)

    def is_component_registered(self, component):
        """
        Check if a component is registered.

        Args:
            component: Component name

        Returns:
            bool: True if component is registered
        """
        return component in self.kb.components
