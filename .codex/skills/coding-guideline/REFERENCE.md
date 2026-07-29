# Reference

## 1) Pre-implementation scan

Before writing code:
- inspect nearby modules and existing feature pages
- check whether equivalent logic already exists
- prefer extension/reuse over reimplementation

If duplicate-risk exists, pause and ask user before coding.

## 2) Modularity expectations

- Keep one responsibility per module.
- Keep orchestrating run-loop logic in runner-like components.
- Keep policy logic side-effect free.
- Keep persistence and logging concerns isolated.
- Avoid ad-hoc utilities placed in unrelated files.

## 3) Rule-violation handling

For each violation discovered in current scope:
- classify: `legacy exception` or `new drift`
- if legacy exception is intended, document it
- if drift is accidental, propose a fix path

Never normalize non-compliant code by adding more non-compliant code.

## 4) Temporary behavior governance

Temporary behavior includes:
- mock outputs
- fallback stubs
- compatibility aliases
- bypass toggles

Required actions:
- document in `docs/legacy/<topic>.md` with context, related files, and removal condition
- annotate implementation with brief temporary comment and removal trigger
- add test coverage that makes removal and migration explicit

## 5) Observability and error handling

Every non-trivial behavior change must be observable through LogBroker.

Required actions:
- define the expected normal events before or during implementation
- define expected error events with stable error codes and recovery behavior
- use `info` for expected durable milestones, `warn` for recoverable abnormal behavior, `error` for failed operations, and `fatal` for critical/unhealthy sessions
- avoid broad catch blocks whose only purpose is logging
- ensure every non-rethrowing `except` calls `capture_exception(...)` or carries a one-line justification comment
- never use bare `print`, unstructured `logging.*`, raw file writes, or raw JSONL parsing as the primary diagnostic path
- never log raw secrets, tokens, credentials, unfiltered database dumps, or conversational transcripts

Standard LogBroker instrumentation that directly supports requested feature work does not require a separate new-logic confirmation. New permanent channels, new fallback behavior, new mocks, new bypasses, and new business paths still require the question protocol.

## 6) Debug-session workflow

When diagnosing a bug:
- create or reuse the active `/debug` session
- write a debug plan before non-trivial changes
- link every relevant app run with `python -m observability.cli debug link-app-session --app-session latest --json`
- tie temporary `TEMP:*` logs and `debug_checkpoint(...)` probes to a hypothesis
- inspect logs through `python -m observability.cli ...`, not raw JSONL parsing
- record important observations, decisions, and patches in the debug session
- keep debug mode open until validation criteria are satisfied
- remove, disable, or promote temporary probes before closure
- run `python -m observability.cli debug check-cleanup --debug-session latest --json`
- write `resolution-report.md` before resolving

## 7) Resolving "last session"

When the user says "last session":
- outside debug mode, use `python -m observability.cli ... --session latest`
- inside debug mode, resolve `--debug-session latest` and inspect linked app sessions
- if the user just performed a manual test, link `--app-session latest` to the active debug session before querying
- if ambiguous, inspect both `debug status --debug-session latest --json` and `logs summary --session latest --json`, then state which session was used
- do not ask the user to copy JSONL paths unless the CLI cannot resolve the session

## 8) Index and traceability

When adding or changing governed backend feature structures:
- update feature `INDEX.md` in same PR/change
- list new classes/components with responsibility and key methods
- reference validation/tests covering them

## 9) Validation and close-out

Before completion:
- run targeted tests or compile checks
- run the relevant manual/e2e feature path when automatic tests do not cover the behavior
- query official logs for latest app/debug session
- compare observed logs against the Observability / Test Contract
- report missing expected logs, unexpected warnings/errors, and what could not be run
- report residual risks and pending migrations
