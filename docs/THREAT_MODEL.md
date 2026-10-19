# Project 16 threat model — bounded local reference system

## Scope, trust, and actors

- Protected asset: two synthetic lookup documents, scope-specific output, human-review decision, local evidence integrity.
- Attack interface: `LocalRequest.untrusted_text`, `operation`, `resource_id`, and caller-supplied scopes. Local `scopes` are the supplied **test harness identity**, not an identity-provider authorization mechanism. In production, scopes must be issued and authenticated by trusted infrastructure.
- Trust boundary: untrusted text may never grant scopes, overwrite reference answer/citation, or authorize a consequential write. The adapter ignores untrusted text entirely, which is a useful bounded regression but cannot model true LLM behavior.
- Adversary scenarios: direct prompt injection, faux role/scope spoof, extraneous retrieved-instruction text passed as `untrusted_text`, secrets/system-prompt requests (no real secrets exist), exfiltration phrasing, tool escalation, approval forgery, resource-unknown abstention, cross-session claims, context flooding.
- Failure actors: artificially injected timeout/rate limit/malformed/auth errors; idempotency replay; circuit breaker. No actual penetration test, real service dependency or network access.

## Safety invariants

1. Reject read lacking exact scope, unsupported operations and write without record:write.
2. Return REVIEW (not ALLOW) for properly scoped write proposals; no external side effects.
3. Allow useful public/private reads only with their exact documented scope and grounded citation.
4. Report overblocking as a measurable risk and block candidates that fail legitimate tasks.
5. Keep all credentials out of ZIP, reports, log exports and screenshots. The deliverable retains `.env.example` ONLY.
6. Fail closed for corrupted locked fixtures, gate policy, prior baseline artifacts and evidence manifest.
7. Separate synthetic latencies from actual CPU time and synthetic risk labels from real-world outcomes.

## Out-of-scope/unverified

A real model responding to prompt injection, cross-tenant identity, SSRF, authentic secret stores, network exfiltration, operating-system command execution, cloud infrastructure, signed attestations, protected-attribute fairness, third-party load, and real rollback are NOT established by the current project. These require independent assessment before making real-world assurances.
