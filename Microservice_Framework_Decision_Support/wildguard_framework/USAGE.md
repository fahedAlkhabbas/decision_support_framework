> **Note:** this document describes version 1 of the code. For version 2 (revision) see the top-level README.md, EXPERIMENTS.md and MODEL.md; some function signatures below have changed.

# WildGuard Framework - Usage Guide

## Installation

### Option 1: Direct Usage (No Installation)

Simply clone or download the framework and run it directly:

```bash
cd /path/to/wildguard_framework
python main.py
```

Or use the standalone runner:

```bash
python run.py
```

### Option 2: Install as a Package

Install the framework as a Python package:

```bash
cd /path/to/wildguard_framework
pip install -e .
```

Then run from anywhere:

```bash
python -m wildguard_framework
```

Or use the command-line tool:

```bash
wildguard-deploy
```

## Running the Framework

### Method 1: Direct Script Execution

From the framework directory:

```bash
python main.py
```

From any directory:

```bash
python /path/to/wildguard_framework/main.py
```

### Method 2: Using the Standalone Runner

```bash
python /path/to/wildguard_framework/run.py
```

### Method 3: Module Execution (After Installation)

```bash
python -m wildguard_framework
```

### Method 4: Command-Line Tool (After Installation)

```bash
wildguard-deploy
```

## Basic Usage in Your Code

### Simple Deployment

```python
import sys
sys.path.insert(0, '/path/to/wildguard_framework')

from ui.user_interface import UserInterface

# Create the framework interface
ui = UserInterface()

# Define system requirements
system_nfrs = {
    "availability": 99.5,
    "performance": {
        "max_delay": 5000,
        "min_throughput": 30
    },
    "security": 96,
}

# Run deployment scenario
ok, time_taken, energy, used_nodes = ui.run_deployment_scenario(
    num_nodes=40,
    system_nfrs=system_nfrs,
    objective="minimize"  # or "feasible" or "maximize"
)

if ok:
    print(f"Deployment successful!")
    print(f"Time: {time_taken:.3f}s, Energy: {energy}")
    print(f"Used nodes: {len(used_nodes)}")
else:
    print("No feasible deployment found")
```

### Access Individual Components

```python
from ui.user_interface import UserInterface

ui = UserInterface()

# Access knowledge base
kb = ui.get_knowledge_base()
print(f"Components: {kb.components}")
print(f"Data flows: {kb.dataflow_paths}")

# Access infrastructure
infra = ui.get_infrastructure_manager()
print(f"Nodes: {infra.nodes}")
print(f"Node tiers: {infra.get_node_count_by_tier()}")

# Access reporting
reporter = ui.get_reporting_manager()
reporter.print_used_nodes("Deployment:", used_nodes)
```

### Use Individual Modules

```python
from core.knowledge_base import KnowledgeBase
from infrastructure.infrastructure_manager import InfrastructureManager
from configuration.configuration_manager import ConfigurationManager

# Create knowledge base
kb = KnowledgeBase()

# Instantiate infrastructure
infra = InfrastructureManager()
nodes, caps, comm = infra.instantiate_infrastructure(50)

# Validate configuration
config = ConfigurationManager(kb)
system_nfrs = {
    "availability": 99.5,
    "performance": {"max_delay": 5000, "min_throughput": 30},
    "security": 96,
}
config.validate_user_input(system_nfrs, kb.dataflow_paths, kb.latency_constraints)
```

## Optimization Objectives

The framework supports three optimization objectives:

### 1. Feasible (Default)

Find any valid deployment without optimization:

```python
ok, time, energy, nodes = ui.run_deployment_scenario(
    num_nodes=40,
    system_nfrs=system_nfrs,
    objective="feasible"
)
```

### 2. Minimize Energy

Find the deployment with minimum energy consumption:

```python
ok, time, energy, nodes = ui.run_deployment_scenario(
    num_nodes=40,
    system_nfrs=system_nfrs,
    objective="minimize"
)
```

### 3. Maximize Energy

Find the deployment with maximum energy consumption (for comparison):

```python
ok, time, energy, nodes = ui.run_deployment_scenario(
    num_nodes=40,
    system_nfrs=system_nfrs,
    objective="maximize"
)
```

## Customizing System Requirements

Modify the system NFRs to test different scenarios:

```python
# Strict requirements
strict_nfrs = {
    "availability": 99.99,  # Very high availability
    "performance": {
        "max_delay": 1000,   # Tight latency constraint
        "min_throughput": 100  # High throughput requirement
    },
    "security": 99,  # Very high security
}

# Relaxed requirements
relaxed_nfrs = {
    "availability": 95.0,  # Lower availability
    "performance": {
        "max_delay": 10000,  # Loose latency constraint
        "min_throughput": 10  # Low throughput requirement
    },
    "security": 80,  # Moderate security
}
```

## Testing Different Infrastructure Sizes

```python
from ui.user_interface import UserInterface

ui = UserInterface()

system_nfrs = {
    "availability": 99.5,
    "performance": {"max_delay": 5000, "min_throughput": 30},
    "security": 96,
}

# Test with different numbers of nodes
for num_nodes in [10, 20, 40, 80]:
    print(f"\n--- Testing with {num_nodes} nodes ---")
    ok, time, energy, nodes = ui.run_deployment_scenario(
        num_nodes=num_nodes,
        system_nfrs=system_nfrs,
        objective="minimize"
    )
    if ok:
        print(f"Success: {len(nodes)} nodes used, {energy} energy, {time:.3f}s")
    else:
        print("No feasible deployment found")
```

## Accessing Results

After running a deployment scenario:

```python
ok, time_taken, energy, used_nodes = ui.run_deployment_scenario(...)

# Check if deployment was successful
if ok:
    print(f"Deployment successful")
    
    # Get timing information
    print(f"Solve time: {time_taken:.3f} seconds")
    
    # Get energy consumption
    print(f"Total energy: {energy} units")
    
    # Get used nodes
    print(f"Number of nodes used: {len(used_nodes)}")
    
    # Get node distribution
    node_counts = ui.get_infrastructure_manager().get_node_count_by_tier()
    print(f"Node distribution: {node_counts}")
    
    # Get component assignments
    # (requires accessing the solver directly through the UI)
else:
    print("No feasible deployment found")
```

## Troubleshooting

### ModuleNotFoundError: No module named 'core'

**Solution**: Make sure you're running from the correct directory or using one of the recommended methods:

```bash
# From the framework directory
cd /path/to/wildguard_framework
python main.py

# Or use the standalone runner
python run.py

# Or install and use as a module
pip install -e .
python -m wildguard_framework
```

### ImportError: No module named 'ortools'

**Solution**: Install the required dependencies:

```bash
pip install ortools psutil
```

### No feasible deployment found

**Possible causes**:
- System requirements are too strict
- Infrastructure is too small
- Constraints are conflicting

**Solution**: Try relaxing the requirements:

```python
# Reduce availability requirement
system_nfrs["availability"] = 95.0

# Increase max delay
system_nfrs["performance"]["max_delay"] = 10000

# Decrease min throughput
system_nfrs["performance"]["min_throughput"] = 10

# Reduce security requirement
system_nfrs["security"] = 80
```

## Performance Tips

1. **Start with feasible objective**: It's faster than optimization objectives
2. **Use reasonable infrastructure sizes**: 40-80 nodes is typical
3. **Relax constraints gradually**: Start with loose constraints, then tighten
4. **Monitor solve time**: If > 10 seconds, consider relaxing constraints

## Example Scripts

### Complete Example

```python
#!/usr/bin/env python3
import sys
sys.path.insert(0, '/path/to/wildguard_framework')

from ui.user_interface import UserInterface

def main():
    ui = UserInterface()
    
    system_nfrs = {
        "availability": 99.5,
        "performance": {
            "max_delay": 5000,
            "min_throughput": 30
        },
        "security": 96,
    }
    
    print("Testing WildGuard Framework\n")
    
    for objective in ["feasible", "minimize", "maximize"]:
        print(f"\n--- {objective.upper()} ---")
        ok, time, energy, nodes = ui.run_deployment_scenario(
            num_nodes=40,
            system_nfrs=system_nfrs,
            objective=objective
        )
        if ok:
            print(f"Success: {len(nodes)} nodes, {energy} energy, {time:.3f}s")
        else:
            print("Failed")

if __name__ == "__main__":
    main()
```

## Next Steps

1. Read the [README.md](README.md) for framework overview
2. Read the [ARCHITECTURE.md](ARCHITECTURE.md) for technical details
3. Explore the module structure in the framework directory
4. Modify the system requirements to test different scenarios
5. Integrate the framework into your own applications

## Support

For issues or questions:
1. Check the error message and troubleshooting section above
2. Review the ARCHITECTURE.md for component details
3. Examine the module docstrings for API details
4. Check the main.py for usage examples
