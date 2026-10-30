# Reproducing the experiments

All experiments are run by `experiments/run_experiments.py`. Results go to
`results/` (CSV files, `summary.txt`, `explanation_report.md`, `figures/`,
`run_info.json` with platform, Python/OR-Tools versions and all settings).

```bash
pip install -r requirements.txt
cd wildguard_framework
python experiments/run_experiments.py all --quick     # smoke test (~ minutes)
python experiments/run_experiments.py all             # paper settings (hours)
python experiments/run_experiments.py all --workers 8 # fix the number of CP-SAT workers
```

Runs are resumable: rows already present in a CSV are skipped, so an
interrupted campaign is completed by re-running the same command. Use
`--out <dir>` to keep campaigns apart.

## Settings used in the paper

| Experiment | Sizes (nodes) | Instance seeds | Solver settings | Output |
|---|---|---|---|---|
| scalability | 10, 20, ..., 100 | 0-9 (10 instances per size) | 30 s limit; feasible, min-energy, max-energy | `scalability.csv` |
| timelimit | 10, 20, ..., 100 | 0-4 | min-energy with 30 s and 300 s limits (`--limits 30 300 3600` for more) | `timelimit.csv` |
| ablation | 10, 30 | 0-4 | 30 s limit; 12 families + 5 categories + objective removed | `ablation.csv` |
| multiobjective | 20 | 0-2 | 30 s limit per solve; payoff table, 4 Pareto fronts (up to 10 points), weighted sum, lexicographic | `mo_payoff.csv`, `mo_pareto.csv` |
| explain | 20 | 0 | 30 s limit per solve | `explanation_report.md` |

The CP-SAT random seed is 0 (`--solver-seed`). By default CP-SAT uses all
cores. With several workers CP-SAT is not deterministic in time, so
solving times and time-limited solutions may vary slightly between runs.
`--workers 1` gives deterministic search at the cost of speed.

## Infrastructure generator

The generator is in `infrastructure/` and all its parameters are in
`infrastructure/generator_config.py`. An instance is fully determined by its
size and seed. `InfrastructureManager.export_json()` writes an instance to a
file and `load_json()` reads it back.

* **Tiers:** 60% Edge, 30% Fog and the remainder Cloud nodes, using floor
  rounding. For example, 10 nodes give 6 Edge, 3 Fog and 1 Cloud.
* **Node attributes** are uniform integers in the ranges below.

| Attribute | Edge | Fog | Cloud |
|---|---|---|---|
| vCPU / memory (GB) | 4 / 8 | 16 / 64 | 64 / 256 |
| throughput capacity (events/s) | 50-120 | 300-500 | 800-1000 |
| energy cost (units) | 25-45 | 180-250 | 600-1100 |
| processing delay (ms) | 2-10 | 10-20 | 2-10 |
| privacy level | high | intermediate | low |
| MTBF (h) | 400-2500 | 1000-3000 | 1500-5000 |
| encryption compliance | 96-99 | 95-99 | 97-99 |
| cost per vCPU-hour (units, illustrative) | 1-5 | 10-30 | 20-60 |
| grid carbon intensity (gCO2e/kWh, illustrative) | 50-400 | 50-400 | 20-700 |

* **Links** are bidirectional and symmetric:
  * each Edge node is linked to 3 random Fog nodes;
  * each Fog node is linked to 2 random Cloud nodes;
  * every other pair is linked with probability 0.7 (same tier), 0.8 (Edge-Fog),
    0.6 (Fog-Cloud) or 0.4 (Edge-Cloud).

| Tier pair | Latency (ms) | Bandwidth (Mbps) |
|---|---|---|
| Edge-Edge | 2-10 | 20-80 |
| Fog-Fog | 10-20 | 200-600 |
| Cloud-Cloud | 2-10 | 500-1000 |
| Edge-Fog | 15-30 | 50-200 |
| Fog-Cloud | 60-120 | 100-400 |
| Edge-Cloud | 70-150 | 20-100 |

* **Random streams:** `random.Random(seed)` draws throughput, energy, delay and
  links (the attributes of the original generator).
  `random.Random(seed + 1000003)` draws MTBF, encryption, cost and carbon
  intensity. `--homogeneous` restores the original values: MTBF 2000 h and
  encryption 96 / 98 / 99 for Edge / Fog / Cloud.

## Scenario

The microservices, their requirements, the data flows, the hop SLAs and the
system NFRs (availability 99.5%, max end-to-end delay 5000 ms, min throughput
30 events/s, security level 96) are in `scenarios/wildfire_intelguard.json`.
To use another system, give `--scenario other.json`.

## Notes on the metrics

* `gap` is CP-SAT's own relative gap $(f-LB)/f$ at termination.
* `fig_gap_vs_nodes` (Fig. 7 of the paper) shows the mean energy of the
  minimum-energy deployments found with each time limit (30 s and 300 s).
  The certified gap reported in `summary.txt` uses the best lower bound found
  by any run on the same instance.
* In `mo_pareto.csv`, `status` is OPTIMAL only if both solves of the
  epsilon-constraint step were optimal (proven Pareto point); otherwise it is
  FEASIBLE (valid deployment, not proven non-dominated). Unproven points are
  drawn as open circles in `fig_pareto`.
* `valid` is 1 only if the independent Validation Manager finds no violation of
  any requirement.
* In the ablation study, `violations` counts violations of the full
  requirement set by the deployment computed without the ablated constraints.
  The `extra` column lists the violated families.
