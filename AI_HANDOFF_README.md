# GrandNexus v6.4 — AI Handoff

## Purpose

This package presents the latest reconstructed GrandNexus architecture to another AI assistant. GrandNexus is not an LLM wrapper. It is a modular cognitive architecture whose core identity is carried by memory, symbolic state, epistemic knowledge, reasoning, planning, metacognition, controlled learning, drives and simulation. LLMs and embeddings are optional proposer/ranking modules.

## Current validated architecture

| Layer | Current state |
|---|---|
| Core orchestration | Modular package with SQLite-backed components |
| Epistemic memory | Observation, hypothesis, validated and rejected statuses |
| Episodic memory | Episodes, state deltas, causal effect index, viability filtering and evaporation |
| Current world state | Persistent, versioned `WorldStateLedger` with provenance, conflicts, restart and rollback |
| Semantic graph | Local graph with epistemic status, provenance and contradiction preservation |
| Planning | Recursive symbolic planning and simulation-only execution |
| Metacognition | Prediction/outcome calibration and observable failures |
| Learning | Explicit, versioned, pending proposals with rollback; no silent promotion |
| Drives | Internal priority signals propose goals but never execute directly |
| LLM | Optional structured proposer in ShadowCycle; deterministic fallback preserved |
| Multi-agent | Experimental proposer/critic/verifier group, isolated from stable truth and action |

## Latest experiment

The first free simulated autonomy run executed 120 cycles without a supplied goal sequence. The `DriveModule` selected objectives from symbolic affordances. GrandNexus adapted to a low-battery perturbation, refused to invent a path while its location was unknown, resumed after state recovery, preserved continuity across a process restart and paused for four cycles while the current-state ledger was conflicted.

The run also exposed a real limitation: after acquiring the one-time novel effects, the system entered a dominant loop among opening/closing a door and moving between home and room. This is not hidden. It indicates that trajectory-level metacognition, novelty/satiation and opportunity cost are still missing.

## Safety and epistemic invariants

1. A perception is not automatically knowledge.
2. An embedding score never establishes truth.
3. An LLM proposal is never a decision or action.
4. Episodic recall does not automatically become current state.
5. The `WorldStateLedger` supplies the coherent current-state snapshot.
6. Contradictions remain visible; unresolved conflicts block planning rather than being silently overwritten.
7. Learning changes remain pending until explicit promotion.
8. All current actions are simulated; hardware-real execution is unavailable.
9. Stable graph mutation and candidate experimentation remain separated.
10. The deterministic core must continue to function when heavy modules are absent or fail.

## Most important files

Read these first inside the consolidated source bundle:

1. `src/grandnexus/integrated_loop.py`
2. `src/grandnexus/world_state_ledger.py`
3. `src/grandnexus/episodic_context.py`
4. `src/grandnexus/autonomy_level1.py`
5. `src/grandnexus/advanced_planner.py`
6. `src/grandnexus/symbolic_planner.py`
7. `src/grandnexus/semantic_knowledge.py`
8. `src/grandnexus/semantic_graph.py`
9. `src/grandnexus/drive_module.py`
10. `src/grandnexus/drive_policy.py`

## Honest maturity assessment

GrandNexus is an advanced cognitive prototype, not a general autonomous intelligence. Its architectural maturity is approximately 14.5–15/20 in the project’s metaphorical scale. Its memory, provenance, conflict handling and deterministic autonomy are demonstrable locally. Generalization, long-duration learning, distributed state, robust trajectory selection and real-world execution are not demonstrated.

## Recommended next step

Do not immediately add another heavy module. First add soft trajectory-level metacognition that detects repetition and low information gain without banning repetition. It may increase the priority of `knowledge_gap` or `memory_maintenance`, but must not manufacture novelty for benchmark performance. Then repeat free simulated autonomy across multiple environments.

Only after stable long-run adaptation should a heavy world-model predictor be introduced behind the symbolic `WorldStateLedger` as an optional transition proposer.

## Review request for another AI

When reviewing this package, distinguish implemented and tested behavior from aspirational modules inherited from the original v6.4 export. Do not infer maturity from class names. Focus on interface consistency, hidden coupling, state persistence, contradiction semantics, restart behavior, learning governance and whether the latest autonomy loop can escape repetitive trajectories without Goodhart-style optimization.
