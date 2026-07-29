# Session Checklist

- [ ] Existing logic scanned before implementation.
- [ ] Duplicate logic risk evaluated and surfaced.
- [ ] New logic announcement emitted when applicable.
- [ ] User confirmation captured for new business-logic or temporary-behavior decisions.
- [ ] Observability / Test Contract defined or updated for every non-trivial behavior change.
- [ ] Expected normal logs listed with channel, feature, event, severity, and correlation strategy.
- [ ] Expected error logs listed with registered error code, severity, trigger condition, and recovery behavior.
- [ ] Temporary debug probes tied to a hypothesis and removal condition.
- [ ] Modularity boundaries respected.
- [ ] Naming conventions respected in changed files.
- [ ] Temporary behavior documented in `docs/legacy/` when added.
- [ ] Temporary behavior commented near implementation in Python.
- [ ] Every non-rethrowing `except` calls `capture_exception(...)` via
      `get_logger(...)`, or carries a one-line justification comment.
- [ ] Durable logs are structured LogBroker events (no bare `print`/strings);
      no raw secrets/PII logged (redaction not bypassed).
- [ ] Targeted unit/contract tests added or updated for behavior changes.
- [ ] Relevant manual/e2e path executed when automatic tests do not cover the observed behavior.
- [ ] Official CLI log checks executed, or explicitly reported as not runnable:
      `logs errors --session latest`, `logs query --session latest`, and when applicable
      `debug summary --debug-session latest`.
- [ ] "Last session" resolved through `latest` pointers and/or the active debug session;
      the user was not asked to copy JSONL paths unless CLI resolution failed.
- [ ] Observed logs compared against the Observability / Test Contract; missing expected
      logs and unexpected warnings/errors surfaced.
- [ ] `/debug` closure (when applicable): validation done, `resolution-report.md`
      written, and human confirmation captured for UI/human-observed bugs.
- [ ] Debug instrumentation cleaned up before closing a debug session:
      every `TEMP:*` channel and `debug_checkpoint(...)` is removed, disabled,
      or promoted to a durable log, and `debug check-cleanup` reports clean.
      See `docs/observability/debug-protocol.md` (it is a text scan, not a full
      lint — confirm intent manually).
- [ ] Feature `INDEX.md` updated when structure/classes changed.
- [ ] Regression tests added/updated for behavior changes.
- [ ] Validation executed (or explicit statement of what could not run).
