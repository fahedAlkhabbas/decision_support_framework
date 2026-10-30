"""
Constraint Manager: encodes the requirements as constraints of the CP-SAT model.

Constraints are organised in *families* so that each family can be switched
off (ablation study) or guarded by an assumption literal (infeasibility
diagnostics). Families and the requirement level they belong to:

  family               level          meaning
  -------------------  -------------  --------------------------------------------------
  capacity             microservice   sum of CPU / memory demands <= node capacity
  throughput_capacity  microservice   sum of service event rates <= node throughput capacity
  ms_response_time     microservice   node processing delay <= service response time
                                       (and service response time <= system max delay)
  ms_mtbf              microservice   node MTBF >= service MTBF requirement
  ms_encryption        microservice   node encryption compliance >= service requirement
  privacy              microservice   node privacy level compatible with service privacy
  system_security      system         every used node meets the system security level
  replication          system         each service has the number of replicas implied
                                       by the system availability target
  min_throughput       system         services in data flows declare >= system throughput
  hop_latency          data flow      proc. delays + link latency <= hop SLA (per hop)
  hop_bandwidth        data flow      link bandwidth >= bandwidth required by the flow
  e2e_delay            system/flow    sum of response times and hop delays of a flow
                                       <= system max end-to-end delay

The placement constraint "every service is deployed at least once" is always on.
"""

from collections import defaultdict

FAMILIES = [
    "capacity",
    "throughput_capacity",
    "ms_response_time",
    "ms_mtbf",
    "ms_encryption",
    "privacy",
    "system_security",
    "replication",
    "min_throughput",
    "hop_latency",
    "hop_bandwidth",
    "e2e_delay",
]

# Requirement categories used in the ablation study (Reviewer 1, comment 4).
# A family can belong to more than one category.
CATEGORIES = {
    "resource_capacity": ["capacity", "throughput_capacity"],
    "microservice_level": ["ms_response_time", "ms_mtbf", "ms_encryption", "privacy"],
    "system_level": ["system_security", "replication", "min_throughput", "e2e_delay"],
    "dataflow": ["hop_latency", "hop_bandwidth", "e2e_delay"],
    "security_privacy": ["privacy", "ms_encryption", "system_security"],
}

# Delay used for a node pair without a direct link (makes the pair unusable).
NO_LINK_LATENCY = 10 ** 6


class ConstraintManager:
    """
    Translates the configurations and the infrastructure into solver-ready
    constraints and attaches them to the model.
    """

    def __init__(self, knowledge_base):
        self.kb = knowledge_base

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def resolve_families(enabled=None, disabled=None):
        """Set of enabled families from an explicit list and/or a list of
        disabled families or categories."""
        fams = set(FAMILIES if enabled is None else enabled)
        for d in disabled or []:
            fams -= set(CATEGORIES.get(d, [d]))
        unknown = fams - set(FAMILIES)
        if unknown:
            raise ValueError(f"Unknown constraint families: {sorted(unknown)}")
        return frozenset(fams)

    def _on(self, dm, fam):
        return fam in dm.enabled_families

    def _gate(self, dm, ct, fam, extra=()):
        """Attach enforcement literals: the family literal (diagnostics mode)
        plus any extra literals."""
        lits = list(extra)
        if dm.family_literals:
            lits.append(dm.family_literals[fam])
        if lits:
            ct.OnlyEnforceIf(lits)
        return ct

    def _forbid_pair(self, dm, fam, a, b):
        """Not both a and b (clause !a v !b), guarded by the family."""
        ct = dm.model.AddBoolOr([a.Not(), b.Not()])
        self._gate(dm, ct, fam)

    # ------------------------------------------------------------------ #
    # static eligibility of a service on a node
    # ------------------------------------------------------------------ #
    def ineligibility_reasons(self, c, n, caps, system_nfrs):
        """Families that exclude service c from node n, independently of where
        the other services are placed."""
        cd = self.kb.comp_requirements[c]
        cap = caps[n]
        reasons = []
        if cap["proc_delay"] > cd["response_time"] or \
                cd["response_time"] > system_nfrs["performance"]["max_delay"]:
            reasons.append("ms_response_time")
        if "mtbf" in cd and cap["mtbf"] < cd["mtbf"]:
            reasons.append("ms_mtbf")
        if "encryption_compliance" in cd and \
                cap["encryption_compliance"] < cd["encryption_compliance"]:
            reasons.append("ms_encryption")
        allowed = set(self.kb.privacy_compatibility[cd.get("privacy", "low")])
        if cap["privacy_capability"] not in allowed:
            reasons.append("privacy")
        if cap["encryption_compliance"] < system_nfrs["security"]:
            reasons.append("system_security")
        if cd["cpu"] > cap["cpu"] or cd["memory"] > cap["memory"]:
            reasons.append("capacity")
        if cd.get("throughput", 0) > cap.get("throughput_cap", 10 ** 9):
            reasons.append("throughput_capacity")
        return reasons

    # ------------------------------------------------------------------ #
    # main entry point
    # ------------------------------------------------------------------ #
    def encode_constraints(self, dm, enabled_families=None, diagnostics=False):
        """
        Encode all enabled constraint families into dm.model.

        Args:
            dm: DeploymentModel (from ModelManager.create_deployment_model)
            enabled_families: iterable of families (default: all)
            diagnostics: if True, every family is guarded by an assumption
                literal so that the solver can report which families conflict.
                In this mode no static pruning is applied.

        Returns:
            DeploymentModel
        """
        dm.enabled_families = frozenset(FAMILIES if enabled_families is None else enabled_families)
        model, A = dm.model, dm.A
        nodes, comps, caps = dm.nodes, dm.components, dm.caps
        nfrs = dm.system_nfrs

        if diagnostics:
            for fam in sorted(dm.enabled_families):
                lit = model.NewBoolVar(f"assume[{fam}]")
                dm.family_literals[fam] = lit
            model.AddAssumptions(list(dm.family_literals.values()))

        # 1. Node eligibility (privacy, MTBF, encryption, response time, system security)
        dm.eligible = {}
        for c in comps:
            elig = []
            for n in nodes:
                reasons = [r for r in self.ineligibility_reasons(c, n, caps, nfrs)
                           if self._on(dm, r)]
                for r in reasons:
                    self._gate(dm, model.Add(A[c, n] == 0), r)
                if diagnostics or not reasons:
                    elig.append(n)
            dm.eligible[c] = elig
        # NB: iterate over these ordered lists (never over sets) so that the
        # model is built identically in every run (reproducibility).
        eligible = dm.eligible

        # 2. Placement and replication (availability)
        dm.replicas = self.kb.replicas_for(nfrs["availability"]) if self._on(dm, "replication") else 1
        for c in comps:
            total = sum(A[c, n] for n in nodes)
            model.Add(total >= 1)                       # always: every service is deployed
            if self._on(dm, "replication"):
                self._gate(dm, model.Add(total == dm.replicas), "replication")
            else:
                model.Add(total == 1)

        # 3. Resource capacities.
        # Written as  load_n <= capacity_n * u_n  (u_n = node n is used). This is
        # equivalent to  load_n <= capacity_n  because u_n = 0 forces load_n = 0,
        # but it gives the solver a much stronger lower bound on objectives that
        # count used nodes (energy, carbon, failure rate), i.e., smaller
        # certified optimality gaps.
        if self._on(dm, "capacity"):
            for n in nodes:
                for r in ("cpu", "memory"):
                    load = sum(self.kb.comp_requirements[c][r] * A[c, n] for c in comps)
                    self._gate(dm, model.Add(load <= caps[n][r] * dm.used[n]), "capacity")
        if self._on(dm, "throughput_capacity"):
            for n in nodes:
                load = sum(self.kb.comp_requirements[c].get("throughput", 0) * A[c, n]
                           for c in comps)
                self._gate(dm, model.Add(load <= caps[n].get("throughput_cap", 10 ** 9) * dm.used[n]),
                           "throughput_capacity")

        # 4. System minimum throughput: services in data flows must sustain it
        if self._on(dm, "min_throughput"):
            min_tp = nfrs["performance"]["min_throughput"]
            for chain in self.kb.dataflow_paths.values():
                for c in chain:
                    if self.kb.comp_requirements[c].get("throughput", min_tp) < min_tp:
                        # requirement cannot be met wherever c is placed
                        for n in nodes:
                            self._gate(dm, model.Add(A[c, n] == 0), "min_throughput")

        # 5. Pairwise hop latency SLAs
        if self._on(dm, "hop_latency"):
            for (c1, c2), max_lat in self.kb.latency_constraints.items():
                for n1 in eligible[c1]:
                    for n2 in eligible[c2]:
                        if n1 == n2:
                            # co-located: the hop costs 2 * processing delay (as in e2e_delay)
                            if 2 * caps[n1]["proc_delay"] > max_lat:
                                self._forbid_pair(dm, "hop_latency", A[c1, n1], A[c2, n2])
                            continue
                        lat = dm.comm.get((n1, n2), {}).get("latency", NO_LINK_LATENCY)
                        if caps[n1]["proc_delay"] + lat + caps[n2]["proc_delay"] > max_lat:
                            self._forbid_pair(dm, "hop_latency", A[c1, n1], A[c2, n2])

        # 6. Per-hop bandwidth along data flows
        if self._on(dm, "hop_bandwidth"):
            required_bw = self.kb.required_bandwidth(nfrs)
            seen = set()
            for _, c1, c2 in self.kb.flow_hops():
                if (c1, c2) in seen:
                    continue
                seen.add((c1, c2))
                for n1 in eligible[c1]:
                    for n2 in eligible[c2]:
                        if n1 == n2:
                            continue
                        bw = dm.comm.get((n1, n2), {}).get("bandwidth", 0)
                        if bw < required_bw:
                            self._forbid_pair(dm, "hop_bandwidth", A[c1, n1], A[c2, n2])

        # 7. End-to-end delay of each data flow
        self._encode_flow_delays(dm, diagnostics)
        return dm

    def _encode_flow_delays(self, dm, diagnostics):
        """
        For each flow f and hop (c, d), y[f,c,d,n1,n2] = x[c,n1] AND x[d,n2].
        Delay of a hop: proc(n1) + latency(n1,n2) + proc(n2), or 2*proc(n) when
        both services share node n. The flow delay is the sum of the response
        times of its services plus the delays of its realised hops.
        Pairs whose hop delay alone already exceeds the bound are forbidden
        directly (no y variable), which is an equivalent but smaller encoding.
        """
        model, A, caps = dm.model, dm.A, dm.caps
        max_delay = dm.system_nfrs["performance"]["max_delay"]
        e2e_on = self._on(dm, "e2e_delay")
        shortcut = e2e_on and not diagnostics
        eligible = dm.eligible

        for fname, chain in self.kb.dataflow_paths.items():
            fixed = sum(self.kb.comp_requirements[c]["response_time"] for c in chain)
            terms = []
            for c, d in zip(chain, chain[1:]):
                for n1 in eligible[c]:
                    for n2 in eligible[d]:
                        if n1 == n2:
                            delay = 2 * caps[n1]["proc_delay"]
                        else:
                            lat = dm.comm.get((n1, n2), {}).get("latency", NO_LINK_LATENCY)
                            delay = caps[n1]["proc_delay"] + lat + caps[n2]["proc_delay"]
                        if fixed + delay > max_delay and shortcut:
                            self._forbid_pair(dm, "e2e_delay", A[c, n1], A[d, n2])
                            continue
                        y = model.NewBoolVar(f"y[{fname},{c},{d},{n1},{n2}]")
                        model.AddMultiplicationEquality(y, [A[c, n1], A[d, n2]])
                        dm.hop_vars[(fname, c, d, n1, n2)] = y
                        terms.append(delay * y)
            expr = fixed + sum(terms)
            dm.flow_delay[fname] = expr
            if e2e_on:
                self._gate(dm, model.Add(expr <= max_delay), "e2e_delay")
