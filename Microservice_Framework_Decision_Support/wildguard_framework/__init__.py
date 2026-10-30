"""
Decision-support framework for deploying microservice-based IoT systems.

Implements the framework described in the paper "A Decision-support Framework
for Deploying Microservice-based IoT Systems". The modules use absolute
imports relative to this directory, which is therefore added to sys.path.
"""

import os as _os
import sys as _sys

__version__ = "2.0.0"

_here = _os.path.dirname(_os.path.abspath(__file__))
if _here not in _sys.path:
    _sys.path.insert(0, _here)

from core.knowledge_base import KnowledgeBase                          # noqa: E402
from components.component_catalog import ComponentCatalogManager      # noqa: E402
from infrastructure.infrastructure_manager import InfrastructureManager  # noqa: E402
from infrastructure.generator_config import GeneratorConfig           # noqa: E402
from configuration.configuration_manager import ConfigurationManager  # noqa: E402
from models.model_manager import ModelManager, DeploymentModel        # noqa: E402
from constraints.constraint_manager import ConstraintManager, FAMILIES, CATEGORIES  # noqa: E402
from solution.solution_manager import SolutionManager, SolveResult    # noqa: E402
from solution.multi_objective import MultiObjectiveOptimizer          # noqa: E402
from validation.validation_manager import ValidationManager           # noqa: E402
from reporting.reporting_manager import ReportingManager              # noqa: E402
from ui.user_interface import UserInterface                           # noqa: E402

__all__ = [
    "KnowledgeBase", "ComponentCatalogManager", "InfrastructureManager", "GeneratorConfig",
    "ConfigurationManager", "ModelManager", "DeploymentModel", "ConstraintManager",
    "FAMILIES", "CATEGORIES", "SolutionManager", "SolveResult", "MultiObjectiveOptimizer",
    "ValidationManager", "ReportingManager", "UserInterface",
]
