> **Note:** this document describes version 1 of the code. For version 2 (revision) see the top-level README.md, EXPERIMENTS.md and MODEL.md; some function signatures below have changed.

# Quick Start Guide

## Installation

### Prerequisites
- Python 3.7 or higher
- pip (Python package manager)

### Step 1: Install Dependencies

```bash
pip install ortools psutil
```

## Running the Framework

### Method 1: From the Framework Directory (Recommended)

```bash
cd /path/to/wildguard_framework
python main.py
```

### Method 2: Using the Standalone Runner

```bash
python /path/to/wildguard_framework/run.py
```

### Method 3: Install as a Package

```bash
cd /path/to/wildguard_framework
pip install -e .
python -m wildguard_framework
```

## Expected Output

When you run the framework, you should see output like:

```
*** Testing on 40 nodes ***
   SolveTime=0.173s  Energy=865
   Nodes Used: Edge=6, Fog=3, Cloud=0
   Used node list:
   Edge (6): EdgeNode0, EdgeNode1, EdgeNode2, EdgeNode3, EdgeNode4, EdgeNode5
   Fog (3): FogNode0, FogNode1, FogNode2
   Cloud (0): -

-- FEASIBLE Deployment (Random Energy) --
   CPU_time≈0.003s  RAM≈45.2MB

-- BEST-ENERGY (MINIMIZED) Deployment --
   CPU_time≈0.003s  RAM≈45.1MB

-- WORST-ENERGY (MAXIMIZED) Deployment --
   CPU_time≈0.003s  RAM≈45.3MB

============================================================
DEPLOYMENT SUMMARY
============================================================
  Nodes |  F_Time | F_Energy | B_Time | B_Energy | W_Time | W_Energy |  Saved | CPU_avg(s) | RAM_avg(MB)
--------+---------+----------+--------+----------+--------+----------+--------+------------+------------
    40 |    0.17 |      865 |   0.17 |      865 |   0.17 |      865 |      0 |      0.003 |       45.2
```

## Fixing Import Errors

If you get `ModuleNotFoundError: No module named 'core'`:

**Solution 1**: Run from the framework directory
```bash
cd /path/to/wildguard_framework
python main.py
```

**Solution 2**: Use the standalone runner
```bash
python /path/to/wildguard_framework/run.py
```

**Solution 3**: Install as a package
```bash
cd /path/to/wildguard_framework
pip install -e .
python -m wildguard_framework
```

## Using in Your Own Code

### Simple Example

```python
import sys
sys.path.insert(0, '/path/to/wildguard_framework')

from ui.user_interface import UserInterface

ui = UserInterface()

system_nfrs = {
    "availability": 99.5,
    "performance": {
        "max_delay": 5000,
        "min_throughput": 30
    },
    "security": 96,
}

ok, time, energy, nodes = ui.run_deployment_scenario(
    num_nodes=40,
    system_nfrs=system_nfrs,
    objective="minimize"
)

if ok:
    print(f"Deployment successful!")
    print(f"Time: {time:.3f}s, Energy: {energy}")
else:
    print("No feasible deployment found")
```

## File Structure

```
wildguard_framework/
├── main.py                    # Main entry point
├── run.py                     # Standalone runner
├── setup.py                   # Package setup
├── __main__.py                # Module entry point
├── README.md                  # Full documentation
├── ARCHITECTURE.md            # Architecture details
├── USAGE.md                   # Detailed usage guide
├── QUICKSTART.md              # This file
│
├── core/                      # Core utilities
│   ├── utilities.py
│   └── knowledge_base.py
│
├── components/                # Microservices management
│   └── component_catalog.py
│
├── infrastructure/            # Infrastructure management
│   ├── node_manager.py
│   ├── network_manager.py
│   └── infrastructure_manager.py
│
├── configuration/             # Configuration management
│   └── configuration_manager.py
│
├── models/                    # Optimization model
│   └── model_manager.py
│
├── constraints/               # Constraint encoding
│   └── constraint_manager.py
│
├── solution/                  # Solver execution
│   └── solution_manager.py
│
├── validation/                # Validation
│   └── validation_manager.py
│
├── reporting/                 # Reporting
│   └── reporting_manager.py
│
└── ui/                        # User interface
    └── user_interface.py
```

## Next Steps

1. **Run the framework** using one of the methods above
2. **Read USAGE.md** for detailed usage instructions
3. **Read ARCHITECTURE.md** for technical details
4. **Explore the code** in the module directories
5. **Modify system requirements** to test different scenarios

## Troubleshooting

### Issue: `ModuleNotFoundError: No module named 'ortools'`
**Solution**: `pip install ortools`

### Issue: `ModuleNotFoundError: No module named 'psutil'`
**Solution**: `pip install psutil`

### Issue: `ModuleNotFoundError: No module named 'core'`
**Solution**: See "Fixing Import Errors" section above

### Issue: No feasible deployment found
**Solution**: Try relaxing the system requirements:
- Reduce `availability` from 99.5 to 95.0
- Increase `max_delay` from 5000 to 10000
- Decrease `min_throughput` from 30 to 10
- Reduce `security` from 96 to 80

## Support

For more information:
- See USAGE.md for detailed usage examples
- See ARCHITECTURE.md for technical architecture
- See README.md for complete documentation
- Review the module docstrings in the code

## Key Features

✓ **Modular Architecture**: 10 independent components
✓ **Flexible Optimization**: Feasible, minimize, or maximize energy
✓ **Comprehensive Constraints**: Resource, latency, privacy, security
✓ **WildGuard Scenario**: Complete drone surveillance system
✓ **Easy Integration**: Simple Python API
✓ **Well Documented**: Extensive documentation and examples
