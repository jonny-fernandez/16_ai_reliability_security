# CP1 — Reference System and Evaluation Contract

## What is under test

`LocalReferenceAdapter` is a **synthetic, local, read-only reference AI-assistant stand-in**, not an actual LLM or hosted system. It can look up two synthetic documents by ID, check two read scopes, or request human review for a proposed write. A caller's `untrusted_text` is handled as data, never as authority. There are **zero actual writes or API calls**. CP1 therefore validates plumbing and an exact-match oracle, NOT real-world prompt-injection resilience, model fairness, model grounding, or production uptime.

## Trust boundary and security assumptions

The evaluator controls versioned fixtures and labels. The adapter is an untrusted system under test, while the fixture-oracle's explicit expected observation is authoritative for this CP1 exercise. The harness supplies `scopes` as trusted evaluation context; the `untrusted_text` field must not grant scopes. This local reference does not authenticate clients and must not be exposed as a real service. Known synthetic docs must be answered verbatim with document citations. Unknown docs require `ABSTAIN`; missing scope requires `DENY`; authorized write proposals require `REVIEW`, not execution. No credential file is loaded.

## Evaluation unit and locked evidence

A case is one stateless adapter invocation with `payload`, an expected `decision`, a `reason_code`, an optional grounded answer + citation, and an expected zero side-effect count. All expected fields are checked exactly. Case IDs must be unique, and the schema has strict validation. The fixture has a SHA-256 sidecar to detect changes when the expected checksum remains trusted; it is not a signature against an attacker able to modify both files. Its ten records are **development fixtures**, not a locked final holdout set. CP3 will define final holdout methodology and prevent tuning after freezing it.

## Acceptance for CP1

- All original and new unit tests pass on the user's Windows environment.
- `python -m ai_reliability.cli cp1` reports 10/10 exact-match reference scenarios, including two legitimate ALLOWs, multiple DENYs, ABSTAIN, and REVIEW.
- The evaluator detects a deliberately unsafe candidate; altered/missing fixture hashes fail closed.
- `outputs/cp1_baseline_report.json` contains per-case evidence, summary counts, and the fixture hash, with zero provider calls or consequential writes.
- This is not a Project 16 release PASS and not evidence of model security in production.

## Risk taxonomy and known limitations

Development scenarios cover ordinary utility, missing permissions, prompt-text injection against scope checking, unknown resource abstention, and the human-approval boundary. They do not model complex RAG, LLM sampling, indirect retrieval attacks, stateful agents, side channels, latency distributions, subgroup fairness, live integrations, or genuine attack success probabilities. These are allocated to later checkpoints.
