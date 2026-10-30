# Formal model

This document gives the constraint model implemented in
`models/model_manager.py`, `constraints/constraint_manager.py` and
`solution/objectives.py`.

## Input

| Symbol | Meaning | Source |
|---|---|---|
| $S$ | microservices | scenario `components` |
| $N$ | infrastructure nodes | generator / instance file |
| $\ell_{nm}, b_{nm}$ | latency (ms) and bandwidth (Mbps) of link $(n,m)$; $\ell_{nm}=\infty$, $b_{nm}=0$ if there is no link | generator |
| $F$ | data flows; flow $f=(s_1,\dots,s_k)$ is an ordered chain of services | scenario `dataflows` |
| $H_f=\{(s_i,s_{i+1})\}$ | hops of flow $f$; $H=\bigcup_f H_f$ | |
| $P\subseteq S\times S$ | service pairs with a hop latency SLA $\lambda_{st}$ | scenario `latency_constraints` |
| $c_s, m_s, \theta_s$ | CPU, memory and event-rate demand of $s$ | scenario |
| $\rho_s, \mu_s, \varepsilon_s, \pi_s$ | required response time, MTBF, encryption compliance, privacy level of $s$ | scenario |
| $C_n, M_n, \Theta_n$ | CPU, memory and throughput capacity of $n$ | generator |
| $d_n, \mathit{MTBF}_n, \mathit{ENC}_n, \Pi_n$ | processing delay, MTBF, encryption compliance, privacy level of $n$ | generator |
| $e_n, g_n, k_n$ | energy cost, carbon (energy × grid intensity / 100), cost per vCPU of $n$ | generator |
| $D, \Theta, \sigma, \alpha$ | system max end-to-end delay, min throughput, security level, availability | system NFRs |
| $r(\alpha)$ | replicas per service implied by $\alpha$ (replication policy) | scenario |
| $\beta$ | bandwidth per event/s | scenario |

Hop delay between consecutive services placed on $n$ and $m$:
$\delta_{nm}=d_n+\ell_{nm}+d_m$ if $n\neq m$, and $\delta_{nn}=2d_n$.

## Decision variables

* $x_{s,n}\in\{0,1\}$: service $s$ is deployed on node $n$;
* $u_n\in\{0,1\}$: node $n$ is used (hosts at least one service);
* $y^f_{s,t,n,m}\in\{0,1\}$: hop $(s,t)$ of flow $f$ is realised from $n$ to $m$.

## Constraints (families)

Node eligibility. $E_s\subseteq N$ is the set of nodes that satisfy all node-local
requirements of $s$:
$n\in E_s \iff d_n\le\rho_s \wedge \rho_s\le D \wedge \mathit{MTBF}_n\ge\mu_s \wedge
\mathit{ENC}_n\ge\varepsilon_s \wedge \Pi_n\in\mathrm{compat}(\pi_s) \wedge \mathit{ENC}_n\ge\sigma$.

| # | Constraint | Family |
|---|---|---|
| (1) | $\sum_n x_{s,n}=r(\alpha)\quad\forall s$ (and $\ge 1$ always) | replication |
| (2) | $x_{s,n}=0\quad\forall s,\ n\notin E_s$ | ms_response_time, ms_mtbf, ms_encryption, privacy, system_security |
| (3) | $\sum_s c_s x_{s,n}\le C_n u_n,\ \sum_s m_s x_{s,n}\le M_n u_n\quad\forall n$ | capacity |
| (4) | $\sum_s \theta_s x_{s,n}\le\Theta_n u_n\quad\forall n$ | throughput_capacity |
| (5) | $\theta_s\ge\Theta\quad\forall s$ in a flow (input consistency) | min_throughput |
| (6) | $u_n=\max_s x_{s,n}\quad\forall n$ | (definition) |
| (7) | $x_{s,n}+x_{t,m}\le1\quad\forall(s,t)\in P,\ n,m\in N,\ \delta_{nm}>\lambda_{st}$ (incl. co-located, $\delta_{nn}=2d_n$) | hop_latency |
| (8) | $x_{s,n}+x_{t,m}\le1\quad\forall(s,t)\in H,\ n\neq m,\ b_{nm}<\beta\Theta$ | hop_bandwidth |
| (9) | $y^f_{s,t,n,m}=x_{s,n}\wedge x_{t,m}$ | (definition) |
| (10) | $\sum_{s\in f}\rho_s+\sum_{(s,t)\in H_f}\sum_{n,m}\delta_{nm}\,y^f_{s,t,n,m}\le D\quad\forall f$ | e2e_delay |

Encoding notes (equivalent reformulations used for efficiency):
(2) is used to prune: variables $y$ and clauses (7)-(8) are created only for
eligible nodes; pairs with $\sum_{s\in f}\rho_s+\delta_{nm}>D$ get the clause
$x_{s,n}+x_{t,m}\le1$ instead of a $y$ variable. Capacities are multiplied by
$u_n$ in (3)-(4): this is equivalent (u_n = 0 forces all x_{s,n} = 0) but yields much
stronger lower bounds for objectives that count used nodes (model version 2.1). In diagnostics mode no pruning is
done and every family is guarded by an assumption literal.

## Objectives (minimised)

| Name | Expression |
|---|---|
| energy | $\sum_n e_n u_n$ |
| carbon | $\sum_n g_n u_n$ |
| cost | $\sum_{s,n} k_n c_s x_{s,n}$ |
| latency | $\sum_f \mathrm{delay}_f$ (left-hand side of (10)) |
| failure_rate | $\sum_n \lfloor 10^6/\mathit{MTBF}_n\rceil u_n$ (series system of used nodes) |
| security_risk | $\sum_{s,n}(100-\mathit{ENC}_n)x_{s,n}$ |

Multi-objective: normalised weighted sum
$\sum_i w_i\,(f_i-f_i^{\mathrm{ideal}})/(f_i^{\mathrm{nadir}}-f_i^{\mathrm{ideal}})$,
lexicographic optimisation with tolerances, and the epsilon-constraint method for
Pareto fronts (`solution/multi_objective.py`).

## Properties

* **NP-completeness.** The feasibility problem is in NP (a deployment is checked
  in polynomial time by `ValidationManager.verify_deployment`). It is strongly
  NP-hard by reduction from BIN PACKING: one service per item with
  $c_s=a_i$, $m_s=\theta_s=0$, identical nodes with $C_n=B$, all nodes eligible,
  no flows and no SLAs, $r=1$. A deployment exists iff the items fit in $|N|$
  bins. With $e_n=1$ the min-energy problem minimises the number of used bins,
  so it is NP-hard and cannot be approximated within a factor $<3/2$ unless P=NP.
* **Model size.** $|S||N|$ placement variables, $|N|$ usage variables and at most
  $\sum_{(s,t)\in H}|E_s||E_t|=O(|H||N|^2)$ hop variables; $O(|S||N|+|P||N|^2+|H||N|^2)$
  constraints. Actual sizes are logged as `model_*` columns in the result CSVs.
* **Soundness.** Every solution of the model satisfies (1)-(10); the Validation
  Manager re-checks each requirement independently of the model before a
  deployment is reported.
* **Completeness.** CP-SAT is a complete solver: without a time limit it returns a
  deployment iff one exists and otherwise proves infeasibility. With a time limit
  the status can be UNKNOWN (no answer) or FEASIBLE (not proven optimal).
* **Optimality certificate.** For optimisation runs CP-SAT reports a proven lower
  bound $LB$; the gap $(f-LB)/f$ bounds the distance to the optimum, also when
  the solver is stopped by the time limit.
* **Monotonicity.** Removing a constraint family can only enlarge the feasible
  set, so the optimal objective value can only decrease. In the ablation study,
  the difference in energy is therefore the price of the removed requirements.
