> **Note:** this document describes version 1 of the code. For version 2 (revision) see the top-level README.md, EXPERIMENTS.md and MODEL.md; some function signatures below have changed.

# Modular Structure Summary

## Overview

The WildGuard Framework has been successfully restructured into **25 modular files** organized into **10 functional packages**, totaling **1,802 lines of code**.

## File Organization

### Package Structure

```
wildguard_framework/
├── 📄 __init__.py                    (Main package init - 44 lines)
├── 📄 main.py                        (Entry point - 68 lines)
├── 📄 README.md                      (User documentation)
├── 📄 ARCHITECTURE.md                (Architecture documentation)
│
├── 📁 core/                          (Core utilities and knowledge)
│   ├── __init__.py
│   ├── utilities.py                  (CPU/RAM utilities - 29 lines)
│   └── knowledge_base.py             (Domain knowledge - 187 lines)
│
├── 📁 components/                    (Microservices management)
│   ├── __init__.py
│   └── component_catalog.py          (Component registry - 76 lines)
│
├── 📁 infrastructure/                (Infrastructure management)
│   ├── __init__.py
│   ├── node_manager.py               (Node creation - 128 lines)
│   ├── network_manager.py            (Network links - 159 lines)
│   └── infrastructure_manager.py     (Orchestration - 85 lines)
│
├── 📁 configuration/                 (Configuration management)
│   ├── __init__.py
│   └── configuration_manager.py      (Input validation - 142 lines)
│
├── 📁 models/                        (Optimization model)
│   ├── __init__.py
│   └── model_manager.py              (Model creation - 80 lines)
│
├── 📁 constraints/                   (Constraint encoding)
│   ├── __init__.py
│   └── constraint_manager.py         (All constraints - 240 lines)
│
├── 📁 solution/                      (Solver execution)
│   ├── __init__.py
│   └── solution_manager.py           (Solving logic - 106 lines)
│
├── 📁 validation/                    (Topology validation)
│   ├── __init__.py
│   └── validation_manager.py         (Verification - 104 lines)
│
├── 📁 reporting/                     (Output formatting)
│   ├── __init__.py
│   └── reporting_manager.py          (Result reporting - 178 lines)
│
└── 📁 ui/                            (User interface)
    ├── __init__.py
    └── user_interface.py             (Main orchestrator - 117 lines)
```

## Module Statistics

| Module | Files | Lines | Purpose |
|--------|-------|-------|---------|
| core | 2 | 216 | Utilities and domain knowledge |
| components | 1 | 76 | Microservices catalog |
| infrastructure | 3 | 372 | Node and network management |
| configuration | 1 | 142 | Input validation |
| models | 1 | 80 | Optimization model |
| constraints | 1 | 240 | Constraint encoding |
| solution | 1 | 106 | Solver execution |
| validation | 1 | 104 | Topology verification |
| reporting | 1 | 178 | Result formatting |
| ui | 1 | 117 | Main orchestrator |
| **Total** | **13** | **1,631** | **Core framework** |

## Key Characteristics

### ✓ Modularity
- Each module has a single, well-defined responsibility
- Clear separation of concerns
- Low coupling between modules
- High cohesion within modules

### ✓ Extensibility
- Easy to add new constraints
- Simple to add new optimization objectives
- Straightforward to extend with new infrastructure types
- Flexible component registration

### ✓ Maintainability
- Clear module naming and organization
- Comprehensive docstrings
- Logical file structure
- Easy to locate specific functionality

### ✓ Testability
- Each module can be tested independently
- Clear interfaces between components
- Minimal external dependencies
- Mockable components

### ✓ Reusability
- Modules can be used in different contexts
- Components are self-contained
- Knowledge base is centralized
- Managers are independently instantiable

## Preserved Elements

### ✓ Logic
- All constraint encoding logic identical
- All optimization objectives preserved
- All data flow handling unchanged
- All resource calculations maintained

### ✓ Assumptions
- Replication semantics: rep=1 unless availability >= 99.9
- Privacy compatibility matrix unchanged
- Node tier characteristics preserved
- Bandwidth and latency calculations identical

### ✓ Scenario
- WildGuard drone system maintained
- All 14 microservices included
- All 4 data flow paths preserved
- All system NFRs and requirements unchanged

## Module Dependencies

```
User Interface
    ↓
┌─────────────────────────────────────┐
│                                     │
Configuration  Infrastructure  Components
Manager        Manager         Catalog
    ↓              ↓                ↓
    └──────────────┼────────────────┘
                   ↓
            Knowledge Base
                   ↓
    ┌──────────────┼────────────────┐
    ↓              ↓                ↓
Model Manager  Constraint Manager  Solution Manager
                   ↓
            Validation Manager
                   ↓
            Reporting Manager
```

## Usage Examples

### Basic Deployment

```python
from wildguard_framework.ui.user_interface import UserInterface

ui = UserInterface()
ok, time, energy, nodes = ui.run_deployment_scenario(
    num_nodes=40,
    system_nfrs={
        "availability": 99.5,
        "performance": {"max_delay": 5000, "min_throughput": 30},
        "security": 96
    },
    objective="minimize"
)
```

### Access Individual Managers

```python
# Access knowledge base
kb = ui.get_knowledge_base()
components = kb.components
dataflows = kb.dataflow_paths

# Access infrastructure
infra = ui.get_infrastructure_manager()
nodes = infra.nodes
capabilities = infra.capabilities

# Access reporting
reporter = ui.get_reporting_manager()
reporter.print_used_nodes("Deployment:", nodes)
```

### Direct Module Usage

```python
from wildguard_framework.core.knowledge_base import KnowledgeBase
from wildguard_framework.infrastructure.infrastructure_manager import InfrastructureManager

kb = KnowledgeBase()
infra = InfrastructureManager()
nodes, caps, comm = infra.instantiate_infrastructure(50)
```

## Testing

All modules have been tested and verified:

```
✓ Core utilities imported
✓ Knowledge base initialized (14 components)
✓ Component catalog validated
✓ Infrastructure managers working
✓ Configuration manager validated
✓ Model manager created (560 variables for 40 nodes)
✓ Constraint manager encoded all constraints
✓ Solution manager ready
✓ Validation manager initialized
✓ Reporting manager initialized
✓ User interface orchestrating all components
```

## Deployment Process

The framework implements the 9-step process from Figure 2 of the paper:

1. **Problem Setup** → User Interface
2. **Validate Input** → Configuration Manager
3. **Instantiate Infrastructure** → Infrastructure Manager
4. **Register Microservices** → Component Catalog Manager
5. **Initialize Model** → Model Manager
6. **Encode Constraints** → Constraint Manager
7. **Solve & Optimize** → Solution Manager
8. **Verify Topologies** → Validation Manager
9. **Report Topologies** → Reporting Manager

## Performance

- **Model Size**: 560 boolean variables (14 components × 40 nodes)
- **Constraint Count**: Thousands (depends on infrastructure)
- **Typical Solve Time**: < 5 seconds
- **Memory Usage**: Proportional to model size
- **CPU Usage**: Tracked via psutil

## Benefits of Modular Structure

1. **Clarity**: Each module's purpose is immediately clear
2. **Maintainability**: Changes are localized to specific modules
3. **Testability**: Each module can be unit tested
4. **Reusability**: Modules can be used independently
5. **Extensibility**: New features are added to appropriate modules
6. **Documentation**: Clear module responsibilities
7. **Collaboration**: Multiple developers can work on different modules
8. **Debugging**: Issues are easier to locate and fix

## Future Extensions

The modular structure makes it easy to add:

- New constraint types (add to ConstraintManager)
- New optimization objectives (add to SolutionManager)
- New infrastructure types (extend NodeManager)
- New validation rules (extend ValidationManager)
- New reporting formats (extend ReportingManager)
- New components (add to KnowledgeBase)

## Conclusion

The WildGuard Framework has been successfully restructured into a modular, maintainable, and extensible architecture while preserving all original logic, assumptions, and the complete WildGuard scenario. The modular structure improves code organization, testability, and future maintainability without changing any of the core functionality or optimization logic.
