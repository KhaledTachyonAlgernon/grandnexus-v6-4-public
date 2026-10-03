# Verification-Experiment Proposer: Shadow-Only Testing of Symbolic Gaps

**Author:** Manus AI  
**Scope:** GrandNexus v6.4, bounded simulated autonomy  
**Status:** Completed palier

## Conclusion

GrandNexus can now convert a `GapHypothesis` into a **candidate verification experiment** without treating the hypothesis as true. The new `VerificationExperimentProposer` accepts only explicitly declared observation capabilities. It checks the current `WorldStateLedger` snapshot, symbolic reachability, planner risk policy, and drive-policy safety gate. It then runs the candidate only inside a `ShadowCycle`, using a temporary ledger and an isolated copy of the graph database.[1] [2]

The implementation preserves the central boundary: a verification experiment may record an `observation:*` effect in its **temporary candidate ledger**, but it may not add, remove, or assert the fact it probes. No candidate result enters the authoritative ledger, semantic graph, or durable semantic knowledge automatically. The complete regression suite passed, including the earlier ledger, episodic-memory, contradiction, LLM-failure, and shadow-memory safeguards.[3]

> `observation:beacon:visible` means that a simulated observation operation was performed. It does **not** mean that `beacon:visible` is true. In this palier, even the observation record remains inside the temporary shadow ledger.

## Operational Contract

A `VerificationCapability` must declare the fact it probes, the symbolic action that carries out the check, and an observation effect in the `observation:*` namespace. The proposer refuses a candidate when the declared action is absent, fails to produce its declared observation effect, changes the probed fact, deletes current-state facts, produces non-observation effects, or does not correspond to the missing precondition of the gap.[1]

The proposer uses the immutable `WorldStateSnapshot` supplied by the autonomy loop. Existing conflicts stop the process before planning. The `AdvancedPlanner` evaluates reachability and rejects paths that exceed its maximum medium-risk threshold. The `DrivePolicy` additionally evaluates the resulting plan as reversible and simulation-only. The shadow candidate then gets its own `WorldStateLedger`; no method of the proposer receives the stable ledger as a mutable target.[2] [4] [5]

The proposer is invoked only during a `trajectory_review` pause after `GapProblemSolver` has returned `hypotheses_available`. The review writes a structured trace event containing the gap, candidate, plan steps, shadow status, and stable-graph invariant. Ordinary autonomous selection resumes after the existing metacognitive cooldown; no verification candidate is executed by the ordinary cognitive loop.[2]

## Safety Evidence

The dedicated unit test establishes four boundaries. A valid observation action completes in shadow and retains `probed_fact_asserted: false`. A malformed action that would produce the probed fact is rejected before shadow execution. A high-risk observation action is rejected by the planner’s risk cap. An unresolved world-state conflict returns `blocked_by_conflict` with no candidate experiment. In all cases, hashes confirm that both the stable graph and authoritative ledger remain unchanged.[3]

The autonomy integration test ran 40 drive-led cycles. It generated six trajectory reviews and six shadow candidates. Each review preserved its authoritative state revision. The stable ledger contained neither `beacon:visible` nor `observation:beacon:visible` after the run. A trace event recorded the isolated result and `stable_unchanged: true` for the review.[6]

| Environment | Accepted cycles | Gap reviews | Shadow verification reviews / candidates | Safety pauses | Result |
|---|---:|---:|---:|---:|---|
| Repetition only | 41 / 48 | 7 | 7 / 7 | 0 | Every relevant review produced one isolated candidate. No observation record or missing fact appeared in the stable state. |
| New opportunity | 43 / 48 | 3 | 2 / 2 | 0 | The environment, not the proposer, injected `beacon:visible`; normal planning later reached `beacon:surveyed`. Fewer gaps required verification afterward. |
| Safety conflict | 39 / 48 | 5 | 5 / 5 | 4 | Contradictory door state caused four existing `verification_first` pauses. The system resumed only after environment-level resolution. |

All environments retained `graph_unchanged: true`, `pending_knowledge: true`, `no_observation_in_stable_state: true`, and unchanged state revisions at trajectory reviews. The result is therefore diagnostic and simulation-only rather than a hidden state-update channel.[7]

## What Has Improved

The previous palier could say that `beacon:visible` was a symbolic condition missing from a route to `beacon:surveyed`. This palier can also form a specific, auditable candidate: `verify_beacon_visibility`, whose only modeled consequence is an observation marker. The candidate is screened through the real planner and safety policy instead of bypassing them. This gives GrandNexus a constrained mechanism for asking, “Can this assumption be tested safely in the current symbolic context?”

The present result remains deliberately incomplete. A successful shadow simulation only shows that a modeled verification sequence is reachable under the action model. It does not provide evidence that the external fact is true, and it does not create a real perception or select a live action. The system still has no automatic mechanism for deciding whether a shadow candidate should be scheduled for a later contained simulation, how to compare informational value across candidates, or how to incorporate an independently supplied observation as an epistemic memory item.

## Recommended Next Palier

The next bounded increment should be a **verification-experiment queue and evaluator**, not real-world execution. It should rank already shadow-validated candidates by expected information gain, novelty, reversibility, and current safety conditions. It should operate only on the existing simulation interfaces, preserve the candidate/stable separation, and submit any result as a versioned observation with provenance. Knowledge promotion must remain a separate, independent-evidence process.

Before any future interface to real perception or hardware, the architecture will need a distinct authority boundary, an explicit operator approval path, and an independently tested perception-to-observation adapter. Those are not part of this palier.

## Reproducibility

The focused suite uses script-style tests and starts with `python3 -m compileall -q src/grandnexus`. The full command sequence and output are preserved in `validation_logs/verification_experiment_proposer_regression.log`. The multienvironment runner uses fresh temporary databases for every environment and writes its observation record to `verification_experiment_multienv_observation.json`.[3] [7]

## References

[1]: https://github.com/KhaledTachyonAlgernon/grandnexus-rebuild/blob/main/src/grandnexus/verification_experiment_proposer.py "VerificationExperimentProposer implementation"
[2]: https://github.com/KhaledTachyonAlgernon/grandnexus-rebuild/blob/main/src/grandnexus/autonomy_level1.py "AutonomyLevelOne verification integration"
[3]: https://github.com/KhaledTachyonAlgernon/grandnexus-rebuild/blob/main/tests/test_verification_experiment_proposer.py "Verification experiment proposer safety test"
[4]: https://github.com/KhaledTachyonAlgernon/grandnexus-rebuild/blob/main/src/grandnexus/world_state_ledger.py "WorldStateLedger implementation"
[5]: https://github.com/KhaledTachyonAlgernon/grandnexus-rebuild/blob/main/src/grandnexus/drive_policy.py "Drive policy safety gate"
[6]: https://github.com/KhaledTachyonAlgernon/grandnexus-rebuild/blob/main/tests/test_verification_experiment_autonomy_integration.py "Verification experiment autonomy integration test"
[7]: https://github.com/KhaledTachyonAlgernon/grandnexus-rebuild/blob/main/tests/run_verification_experiment_multienv.py "Verification experiment multienvironment runner"
