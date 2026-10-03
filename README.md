# GrandNexus v6.4 — Public Snapshot

GrandNexus is a modular cognitive-architecture prototype reconstructed from an earlier notebook export. It is **not an LLM wrapper**. Its operational identity is carried by symbolic state, episodic and semantic memory, provenance, planning, metacognition, slow learning, drives, and simulation.

## Scope of this public snapshot

This repository contains the modular source tree, executable script-style tests, the principal architectural contracts and reports, and the tools used to reproduce the latest bounded experiments. Large historical reference exports, private-session model catalogs, raw session dumps and generated transport archives are intentionally excluded from this public snapshot.

The project remains experimental. Demonstrated behavior is local, deterministic or simulation-bound. Class names and inherited modules must not be interpreted as proof of general intelligence or open autonomy.

## Current verified boundary

The current v6.4 core demonstrates:

- SQLite-backed epistemic and episodic memory layers;
- a persistent `WorldStateLedger` for authoritative simulated current state;
- symbolic planning and simulation;
- graph provenance and conflict visibility;
- drive-led bounded autonomy;
- trajectory-stagnation and symbolic-gap diagnosis;
- shadow-only verification-experiment proposals;
- slow, explicit, auditable and reversible learning proposals;
- deterministic operation when optional LLM components are absent or fail.

The verification-experiment proposer can evaluate a declared observation candidate in an isolated shadow ledger. It does not create the probed fact, write observations into stable state, mutate the stable graph, promote knowledge automatically, or perform real-world actions.

## Safety boundary

All current action paths are simulation-only. The project does not provide an authorization layer for hardware, production infrastructure, accounts, or external side effects. LLMs and heavy models are optional proposers or rankers; they are not truth or action authorities.

## Running focused checks

The project targets Python 3.11 or newer. The primary tests are executable scripts rather than a conventional pytest suite:

```bash
python3 -m compileall -q src/grandnexus
PYTHONPATH=src python3 tests/test_verification_experiment_proposer.py
PYTHONPATH=src python3 tests/test_verification_experiment_autonomy_integration.py
PYTHONPATH=src python3 tests/run_verification_experiment_multienv.py
```

The remaining script-style regression checks are listed in the reports and test directory. Optional dependencies are not required for the deterministic core.

## Roadmap and maturity

The original v6.4 roadmap remains a reference, not a capability claim. GrandNexus is a contained cognitive prototype, not an independent general autonomous intelligence. The next sensible research increments concern longer-running contained experiments, evaluation of shadow verification candidates, durable causal-memory reconstruction and optional transition prediction behind the symbolic ledger.

## License

This public snapshot is released under the Apache License 2.0. See [LICENSE](LICENSE).

## Acknowledgement

This repository is published as a cleaned public snapshot of the `grandnexus-rebuild` development line. The snapshot intentionally preserves candid limitations and separates implemented behavior from aspirational architecture.
