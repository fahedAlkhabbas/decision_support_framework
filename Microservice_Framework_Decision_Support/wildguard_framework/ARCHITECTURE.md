> **Note:** this document describes version 1 of the code. For version 2 (revision) see the top-level README.md, EXPERIMENTS.md and MODEL.md; some function signatures below have changed.

# WildGuard Framework Architecture

## Module Dependency Graph

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INTERFACE (ui/)                      │
│            Orchestrates the complete process                 │
└────────────────────────────┬────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ Configuration    │ │ Infrastructure   │ │ Components       │
│ Manager          │ │ Manager          │ │ Catalog          │
│ (configuration/) │ │ (infrastructure/)│ │ (components/)    │
└────────┬─────────┘ └────────┬─────────┘ └────────┬─────────┘
         │                    │                    │
         │    ┌───────────────┼───────────────┐   │
         │    │               │               │   │
         ▼    ▼               ▼               ▼   ▼
    ┌────────────────────────────────────────────────┐
    │         KNOWLEDGE BASE (core/)                 │
    │  - Microservices catalog                       │
    │  - Data flows                                  │
    │  - Constraints                                 │
    │  - Configuration parameters                   │
    └────────────────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ Model Manager    │ │ Constraint       │ │ Solution         │
│ (models/)        │ │ Manager          │ │ Manager          │
│                  │ │ (constraints/)   │ │ (solution/)      │
└────────┬─────────┘ └────────┬─────────┘ └────────┬─────────┘
         │                    │                    │
         └────────────────────┼────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ Validation       │
                    │ Manager          │
                    │ (validation/)    │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ Reporting        │
                    │ Manager          │
                    │ (reporting/)     │
                    └──────────────────┘
```

## Component Responsibilities

### User Interface (ui/)
- **File**: `user_interface.py`
- **Responsibility**: Orchestrate the complete deployment process
- **Key Methods**:
  - `run_deployment_scenario()`: Main entry point
  - `get_knowledge_base()`: Access KB
  - `get_infrastructure_manager()`: Access infrastructure
  - `get_reporting_manager()`: Access reporting

### Knowledge Base (core/)
- **File**: `knowledge_base.py`
- **Responsibility**: Store all domain knowledge
- **Key Data**:
  - Microservices catalog (14 components)
  - Data flow chains (4 flows)
  - Latency constraints (14 constraints)
  - Privacy compatibility matrix
  - Configuration parameters

### Configuration Manager (configuration/)
- **File**: `configuration_manager.py`
- **Responsibility**: Validate and normalize input
- **Key Methods**:
  - `validate_user_input()`: Validate NFRs, flows, constraints
  - `normalize_specifications()`: Normalize to standard format
  - `validate_dataflow_chain()`: Validate individual flows
  - `validate_nfr_values()`: Check value ranges

### Infrastructure Manager (infrastructure/)
- **Files**: 
  - `node_manager.py`: Create Edge/Fog/Cloud nodes
  - `network_manager.py`: Generate communication links
  - `infrastructure_manager.py`: Orchestrate both
- **Responsibility**: Model and instantiate infrastructure
- **Key Methods**:
  - `instantiate_nodes()`: Create nodes with capacities
  - `generate_links()`: Create network topology
  - `instantiate_infrastructure()`: Complete setup

### Component Catalog Manager (components/)
- **File**: `component_catalog.py`
- **Responsibility**: Manage microservices registry
- **Key Methods**:
  - `validate_and_register_microservices()`: Validate components
  - `get_component_requirements()`: Get component specs
  - `get_all_components()`: List all components
  - `is_component_registered()`: Check registration

### Model Manager (models/)
- **File**: `model_manager.py`
- **Responsibility**: Initialize optimization model
- **Key Methods**:
  - `initialize_model()`: Create CP-SAT model with variables
  - `create_model()`: Create empty model
  - `create_boolean_variable()`: Add bool var
  - `create_integer_variable()`: Add int var

### Constraint Manager (constraints/)
- **File**: `constraint_manager.py`
- **Responsibility**: Encode all constraints
- **Key Methods**:
  - `encode_constraints()`: Main constraint encoding
  - `_add_resource_constraints()`: CPU/memory limits
  - `_add_component_constraints()`: Response time, MTBF, encryption
  - `_add_privacy_constraints()`: Privacy compatibility
  - `_add_latency_constraints()`: Hop-wise SLAs
  - `_add_replication_and_security_constraints()`: Availability, security
  - `_add_throughput_constraints()`: Throughput and bandwidth
  - `_add_dataflow_delay_constraints()`: End-to-end delays

### Solution Manager (solution/)
- **File**: `solution_manager.py`
- **Responsibility**: Execute solver and optimize
- **Key Methods**:
  - `solve_and_optimize()`: Run CP-SAT solver
  - `get_deployment_assignment()`: Extract solution
  - `get_solution_status()`: Get status string
  - `is_solution_feasible()`: Check feasibility
  - `is_solution_optimal()`: Check optimality

### Validation Manager (validation/)
- **File**: `validation_manager.py`
- **Responsibility**: Verify topologies
- **Key Methods**:
  - `verify_topologies()`: Main verification
  - `validate_node_distribution()`: Check node distribution
  - `validate_energy_consumption()`: Check energy
  - `validate_solution_quality()`: Check solve metrics
  - `validate_component_deployment()`: Check all components deployed

### Reporting Manager (reporting/)
- **File**: `reporting_manager.py`
- **Responsibility**: Format output
- **Key Methods**:
  - `report_topologies()`: Print deployment summary
  - `pretty_group_nodes()`: Group nodes by tier
  - `print_used_nodes()`: Print node list
  - `report_deployment_assignment()`: Print component assignments
  - `report_node_utilization()`: Print utilization stats
  - `format_metrics_table()`: Format results table

### Core Utilities (core/)
- **File**: `utilities.py`
- **Responsibility**: Provide utility functions
- **Key Functions**:
  - `get_cpu_ram_usage()`: Measure CPU and RAM

## Data Flow

### Deployment Process Flow

```
1. USER INPUT
   ├─ Microservices requirements
   ├─ System-level NFRs
   ├─ Data flow chains
   └─ Infrastructure size

2. CONFIGURATION VALIDATION
   ├─ Validate NFRs
   ├─ Validate data flows
   ├─ Validate constraints
   └─ Normalize specifications

3. INFRASTRUCTURE INSTANTIATION
   ├─ Create nodes (Edge/Fog/Cloud)
   ├─ Generate network links
   └─ Assign node capabilities

4. MICROSERVICE REGISTRATION
   └─ Validate all components in catalog

5. MODEL INITIALIZATION
   ├─ Create CP-SAT model
   └─ Create binary variables A[c,n]

6. CONSTRAINT ENCODING
   ├─ Resource constraints
   ├─ Component constraints
   ├─ Privacy constraints
   ├─ Latency constraints
   ├─ Security constraints
   ├─ Throughput constraints
   └─ Dataflow delay constraints

7. SOLVING & OPTIMIZATION
   ├─ Run CP-SAT solver
   ├─ Apply optimization objective
   └─ Extract solution

8. VALIDATION
   ├─ Verify topology feasibility
   ├─ Check node distribution
   ├─ Validate energy consumption
   └─ Verify all components deployed

9. REPORTING
   ├─ Format deployment assignment
   ├─ Display node utilization
   ├─ Print metrics table
   └─ Generate recommendations
```

## Module Interaction Sequence

```
User Interface
    │
    ├─> Configuration Manager
    │       └─> Knowledge Base (validate against)
    │
    ├─> Infrastructure Manager
    │       ├─> Node Manager (create nodes)
    │       └─> Network Manager (create links)
    │
    ├─> Component Catalog Manager
    │       └─> Knowledge Base (validate components)
    │
    ├─> Model Manager
    │       └─> Create optimization model
    │
    ├─> Constraint Manager
    │       ├─> Knowledge Base (get constraints)
    │       └─> Add constraints to model
    │
    ├─> Solution Manager
    │       └─> Run solver on model
    │
    ├─> Validation Manager
    │       └─> Verify solution
    │
    └─> Reporting Manager
            └─> Format and display results
```

## Constraint Hierarchy

```
SYSTEM-LEVEL CONSTRAINTS
├─ Availability (replication)
├─ Performance (max delay, min throughput)
└─ Security (encryption compliance)

COMPONENT-LEVEL CONSTRAINTS
├─ Resource requirements (CPU, memory)
├─ Response time
├─ MTBF (Mean Time Between Failures)
└─ Encryption compliance

INFRASTRUCTURE CONSTRAINTS
├─ Node capacity (CPU, memory, throughput)
├─ Link bandwidth
├─ Link latency
└─ Node privacy capability

DATA FLOW CONSTRAINTS
├─ Hop-wise latency SLAs
├─ End-to-end response time
└─ Per-hop bandwidth requirements

PRIVACY & SECURITY CONSTRAINTS
├─ Privacy compatibility (component ↔ node)
└─ Encryption compliance (node ↔ system requirement)
```

## Extensibility Points

### Adding New Constraints
1. Add constraint definition to Knowledge Base
2. Add constraint encoding method to Constraint Manager
3. Call new method from `encode_constraints()`

### Adding New Components
1. Add component to Knowledge Base
2. Define component requirements
3. Framework automatically handles deployment

### Adding New Optimization Objectives
1. Add objective logic to Solution Manager
2. Modify `solve_and_optimize()` method
3. Update reporting for new objective

### Adding New Infrastructure Tiers
1. Modify Node Manager to create new tier
2. Update Network Manager link generation
3. Update Reporting Manager for visualization

## Testing Strategy

Each module can be tested independently:

```python
# Test Knowledge Base
kb = KnowledgeBase()
assert len(kb.components) == 14

# Test Component Catalog
catalog = ComponentCatalogManager(kb)
catalog.validate_and_register_microservices(kb.components)

# Test Infrastructure
infra = InfrastructureManager()
nodes, caps, comm = infra.instantiate_infrastructure(10)

# Test Configuration
config = ConfigurationManager(kb)
config.validate_user_input(nfrs, flows, constraints)

# Test Model
model_mgr = ModelManager(kb, catalog)
model, A = model_mgr.initialize_model(nodes, kb.components)

# Test Constraints
constraint_mgr = ConstraintManager(kb)
model = constraint_mgr.encode_constraints(model, A, nodes, caps, comm, nfrs, kb.components)

# Test Solution
solution_mgr = SolutionManager()
ok, time, energy, used_nodes, solver = solution_mgr.solve_and_optimize(model, A, nodes, caps)

# Test Validation
validation_mgr = ValidationManager()
valid, msg = validation_mgr.verify_topologies(ok, used_nodes, nfrs)

# Test Reporting
reporting_mgr = ReportingManager()
reporting_mgr.report_topologies(ok, time, energy, used_nodes, counts)
```

## Performance Characteristics

- **Model Creation**: O(|components| × |nodes|) variables
- **Constraint Encoding**: O(|constraints| × |nodes|²) constraints
- **Solving**: CP-SAT solver complexity (typically polynomial for this problem)
- **Memory**: Proportional to model size

For 40 nodes and 14 components:
- Variables: 560 boolean variables
- Constraints: Thousands (depends on infrastructure)
- Typical solve time: < 5 seconds
