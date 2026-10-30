This is the prototype implementing the approach in **A Decision-support Framework for Deploying Microservice-based IoT Systems**.

Given a set of microservices with resource and quality requirements, the data
flows between them, system-level non-functional requirements and an
Edge-Fog-Cloud infrastructure, the framework does the following:
* it determines whether a deployment satisfying all requirements exists, and
  explains why when none does;
* it recommends deployments that optimise one or several objectives (energy,
  latency, cost, carbon, failure rate, security risk);
* it explains each recommendation and the trade-offs between alternatives.

## Installation

```bash
pip install -r wildguard_framework/requirements.txt   # ortools, matplotlib
```

Tested with Python 3.12 and OR-Tools 9.x.

## Quick start

```bash
cd wildguard_framework
python main.py --nodes 20 --seed 0                    # min-energy deployment + explanation
python main.py --nodes 20 --seed 0 --objective latency
python main.py --nodes 10 --seed 3                    # infeasible instance -> diagnosis
python main.py --nodes 40 --demo                      # feasible / min / max energy demo
python experiments/run_experiments.py all --quick     # all experiments, small settings
```

* See `EXPERIMENTS.md` to reproduce the experiments of the paper, including the
  generator, seeds and settings.
* See `MODEL.md` for the formal model, its complexity and its properties.

## Project structure

```
wildguard_framework/
├── main.py                       # single explained run (CLI)
├── scenarios/
│   └── wildfire_intelguard.json  # scenario: services, requirements, flows, SLAs, NFRs
├── core/
│   ├── knowledge_base.py         # scenario knowledge + deployment history
│   └── metrics.py                # quality metrics of a deployment
├── components/component_catalog.py
├── configuration/configuration_manager.py
├── infrastructure/
│   ├── generator_config.py       # every generator parameter (documented)
│   ├── node_manager.py           # seeded node generation
│   ├── network_manager.py        # seeded link generation
│   └── infrastructure_manager.py # instance generation, JSON export/import
├── models/model_manager.py       # CP-SAT model + decision variables
├── constraints/constraint_manager.py  # constraint families (ablation, diagnostics)
├── solution/
│   ├── solution_manager.py       # solving, bounds/gap, infeasibility diagnosis
│   ├── objectives.py             # objective expressions
│   └── multi_objective.py        # weighted sum, lexicographic, Pareto fronts
├── validation/validation_manager.py   # independent re-check of every requirement
├── reporting/
│   ├── reporting_manager.py
│   └── explainer.py              # explanations, comparisons, trade-offs
├── ui/user_interface.py          # orchestrates the process
├── experiments/run_experiments.py
└── tests/test_framework.py       # python -m pytest tests -q
```


## Acknowledgement
Parts of the software implementation were developed with the assistance of AI-based tools (ChatGPT, Manus and Claude). The AI tools were used to support code generation, documentation, and some refactoring. 
