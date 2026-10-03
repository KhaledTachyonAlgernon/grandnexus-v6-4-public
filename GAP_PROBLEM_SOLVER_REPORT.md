# GapProblemSolver: Consultative Diagnosis of Symbolic Gaps

**Author:** Manus AI  
**Scope:** GrandNexus v6.4, simulation-only autonomy  
**Status:** Completed palier

## Conclusion

`GapProblemSolver` extends GrandNexus from recognizing an unproductive repeated trajectory to **explaining one bounded class of symbolic blockage**. When trajectory metacognition detects stagnation, the solver inspects the fixed symbolic action model. For a novel effect that remains unavailable because one or more action preconditions are absent, it emits a low-confidence `GapHypothesis` and a verification question. The output is consultative. It is neither a fact, a plan, an action request, nor a knowledge promotion.

The focused regression suite passed on 18 September 2026. It covered the new solver, trajectory detection, drive-led autonomy, the persistent world-state ledger, episodic recall and contradiction handling, deterministic operation under LLM failure, and shadow-memory evaporation. The multienvironment run also confirmed that the stable semantic graph remained unchanged and that the learning state contained no automatically promoted knowledge in all three environments.[1] [2]

> A `GapHypothesis` means that the current **symbolic model** contains a potentially useful but blocked, as-yet-unobserved effect. It does not mean that the missing precondition is true, reachable, or should be created.

## Contract and Boundary

The solver accepts only symbolic `SimAction` descriptions, current simulated facts, observed effects, state conflicts, and the repeated trajectory pattern. It derives candidates from the following limited rule:

1. An action has an effect that is absent both from the current state and from the record of previously observed effects.
2. The same action has at least one precondition absent from the current state.
3. No unresolved world-state conflict exists.

It returns a `GapAnalysis` with either one or more `missing_precondition` hypotheses, `blocked_by_conflict`, `no_symbolic_gap`, or `not_applicable`. Equivalent missing-precondition sets are merged across actions so that the output does not multiply the same question merely because several action paths need it. The confidence is a bounded diagnostic weight, not an evidential confidence in the missing fact itself.[1]

`AutonomyLevelOne` invokes the solver only after `TrajectoryMetacognition` returns `stagnating` and the drive policy selects the temporary `trajectory_review` pause. The result is written to the trace and may be represented in a **pending** slow-learning proposal. Ordinary drive selection then resumes after the existing metacognitive cooldown. The solver cannot call the planner for execution, apply a `WorldStateLedger` transition, mutate the semantic graph, or invoke semantic knowledge promotion.[2]

## Evidence from Tests

The dedicated unit test supplied three checks. First, two independently blocked unobserved effects produced two missing-precondition questions: `beacon:visible` for `survey_beacon` and `archive:unlocked` for `inspect_archive`. Second, an unresolved `door:open` / `door:closed` conflict returned `blocked_by_conflict` and no hypotheses. Third, once the relevant conditions and effects were already present, the result was `no_symbolic_gap`. This shows that the solver does not manufacture a gap merely because a trajectory has repeated.[3]

The complete focused suite passed all twelve requested script-style checks, preceded by `python3 -m compileall -q src/grandnexus`. The regression retained the established guarantees: contradictory episodic contexts are rejected or filtered; ledger conflicts trigger `verification_first`; optional LLM timeout, malformed-output, and quota-failure paths retain deterministic fallback without action authority; and weak shadow memory can evaporate. The raw validation log is retained in the repository for this checkpoint.[4]

| Environment | Accepted simulation cycles | Trajectory reviews | Gap reviews / hypotheses | Safety pauses | Key observation |
|---|---:|---:|---:|---:|---|
| Repetition only | 41 / 48 | 7 | 7 / 7 | 0 | Each review identified the blocked `survey_beacon` pathway, asking whether `at:room, beacon:visible` was available. The system did not assert or create either condition. |
| New opportunity | 43 / 48 | 5 | 3 / 3 | 0 | The environment injected `beacon:visible` at cycle 25. GrandNexus later reached `beacon:surveyed`; subsequent reviews contained fewer symbolic gaps. |
| Safety conflict | 39 / 48 | 5 | 5 / 5 | 4 | The contradictory door facts caused four `verification_first` pauses. Progress resumed only after the environment resolved the conflict. |

All environments reported `pending_knowledge: true` and `graph_unchanged: true`. In particular, injecting a real simulated opportunity enabled a normal planner path; the solver did not claim credit for it and did not synthesize the injected fact.[4]

## What This Changes—and What It Does Not

This palier is a genuine change from **passive repetition detection** to a minimal symbolic explanation of why a potentially novel effect may not be reachable. It is useful because it makes the missing assumption explicit and auditable, rather than treating continued looping as unexplained.

It is **not self-directed exploration**. The current solver cannot choose a verification experiment, rank safe information-gathering actions, request new perception, or execute a test. It also sees only the symbolic actions supplied when `AutonomyLevelOne` is constructed; dynamically adding actions later would require an explicit refresh or a reconstructed autonomy instance. The present multienvironment experiment adds a fact rather than actions, so this limitation does not affect the reported result.[1] [2]

The next palier should therefore be a separate, tightly controlled **verification-experiment proposer**. It may translate a `GapHypothesis` into a simulation-only candidate experiment, but only after planner reachability, `WorldStateLedger` consistency, drive-policy safety, and ShadowCycle evaluation. It must never create missing facts to make an experiment succeed, mutate the stable graph directly, or automatically promote a hypothesis to knowledge.

## Reproducibility

From the repository root, execute the script-style tests with `PYTHONPATH=src`. The focused suite used the exact sequence recorded in `validation_logs/gap_problem_solver_regression.log`; it includes compilation plus the solver, trajectory, autonomy, ledger, episodic, contradiction, core autonomy, failure campaign, and shadow-memory scripts. The multienvironment runner regenerates `trajectory_multienv_observation.json` from fresh temporary SQLite databases, rather than relying on persistent prior state.[4]

## References

[1]: https://github.com/KhaledTachyonAlgernon/grandnexus-rebuild/blob/main/src/grandnexus/gap_problem_solver.py "GapProblemSolver implementation"
[2]: https://github.com/KhaledTachyonAlgernon/grandnexus-rebuild/blob/main/src/grandnexus/autonomy_level1.py "AutonomyLevelOne trajectory integration"
[3]: https://github.com/KhaledTachyonAlgernon/grandnexus-rebuild/blob/main/tests/test_gap_problem_solver.py "GapProblemSolver unit test"
[4]: https://github.com/KhaledTachyonAlgernon/grandnexus-rebuild/blob/main/tests/run_trajectory_multienv.py "Trajectory multienvironment experiment"
