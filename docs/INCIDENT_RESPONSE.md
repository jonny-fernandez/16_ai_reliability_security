# CP3 synthetic incident response workflow

1. **Detect:** The bounded local fault suite classifies timeout/429, malformed response, auth failure, prolonged failure and an open circuit. Each case writes synthetic status and a stable case ID to an offline evidence file.
2. **Triage:** `SEV3` is used for isolated synthetic degradation; `SEV2` for the simulated open-circuit unavailability. The present suite contains no actual data exposure and therefore must not claim real SEV1 events.
3. **Contain:** Malformed/auth failures terminate immediately; timeout/429 retry at most three modeled attempts; exhaustion fails closed or abstains using the explicit read-only fallback. Each case has 0 external writes.
4. **Recommend:** If equivalent REAL telemetry existed, investigate the regression and consider a candidate rollback. In CP3 this is a string in a report, **not an action**. No credentials, deployments or production changes are made.
5. **Preserve evidence:** Generate `cp3_report.json`, offline event and OTel-span JSONL, dashboard CSV and manifest. Validate each SHA-256 value after writing, retaining the caveat that all metadata is unsigned.
6. **Recover:** A human reviewer examines per-case mismatch, retry counts, synthesized SLO impact, environment, and provenance; independently verifies actual service behavior before any real incident response.
7. **Postmortem:** Use `POSTMORTEM_TEMPLATE.md` to record scenario assumptions, deterministic replay inputs, effect of failure injection, false alarms, fixes, and evidence limitations.
