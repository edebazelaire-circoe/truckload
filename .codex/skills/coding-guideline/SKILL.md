---
name: coding-guideline
title: Coding Guideline Guard
type: code
description: Enforces production-grade coding workflow with modularity, regression safety, observability contracts, debug-session validation, and traceability gates. Use when implementing or refactoring code, especially when new logic, mocks, temporary shims, logging, failure handling, tests, or cross-file architecture changes are involved.
tags:
  - code
  - architecture
  - quality
  - governance
conflicts: []
status: active
---

See detailed guidance:
- [REFERENCE.md](REFERENCE.md)
- [QUESTION_PROTOCOL.md](QUESTION_PROTOCOL.md)
- [CHECKLIST.md](CHECKLIST.md)

# Purpose

Use this skill to keep coding sessions aligned with backend governance, modularity, regression safety, and LogBroker-based observability.

# Mandatory workflow

1. Scan existing logic before implementing.
2. Announce new business logic with `IMPLEMENTING NEW LOGIC - <name>: <short reason>`.
3. Ask confirmation before adding new business logic or temporary behavior.
4. Keep modular boundaries and update docs/tests with the change.
5. Add an Observability / Test Contract for every non-trivial behavior change.
6. Run targeted validation and inspect official LogBroker output before claiming completion.

# Observability / Test Contract

For each non-trivial feature or fix, record:
- feature and LogBroker channel
- correlation id strategy
- expected normal events and when they must appear
- expected failure events, stable codes, and recovery behavior
- temporary debug probes, hypothesis, and removal condition
- tests and CLI log queries to run

Normal expected flow must not be logged as a failure. Use durable info events for normal milestones, temporary debug probes only while diagnosing, warnings for recoverable abnormal behavior, and failure events only when an operation fails.

Standard LogBroker instrumentation, exception capture, and validation logs that directly support the requested feature do not require separate new-logic confirmation. New permanent channels, new fallback behavior, mocks, temporary overrides, and new business paths still require the question protocol.

# Debug and log-validation workflow

Use the official CLI/query API, not raw JSONL parsing, except as a last-resort fallback.

For feature work, run relevant tests and query latest logs with:
- `python -m observability.cli logs errors --session latest --json`
- `python -m observability.cli logs query --session latest --correlation-id <id> --json`
- `python -m observability.cli logs summary --session latest --json`

In `/debug` mode, link the latest app run and inspect debug state with:
- `python -m observability.cli debug link-app-session --app-session latest --json`
- `python -m observability.cli debug status --debug-session latest --json`
- `python -m observability.cli debug summary --debug-session latest --json`
- `python -m observability.cli debug check-cleanup --debug-session latest --json`

Closure requires validation, cleanup, and `resolution-report.md`.

# Resolving "last session"

Outside debug mode, treat "last session" as `--session latest`. In debug mode, resolve `--debug-session latest`, inspect linked app sessions, and link `--app-session latest` if the user just performed a manual test. Do not ask the user to copy JSONL paths unless CLI resolution fails.

# Non-negotiable gates

- Temporary behavior is documented in `docs/legacy/*.md` and commented near implementation.
- Governed feature structure changes update the feature `INDEX.md`.
- Behavior changes add or update regression tests.
- Non-rethrowing catches capture the exception or justify silence.
- Durable logs are structured LogBroker events.
- Expected logs from the Observability / Test Contract are checked through the official CLI.
- `/debug` closure removes, disables, or promotes all temporary probes and passes cleanup.

# Clean code

Prioritize readability, explicit names, focused methods, cohesive modules, predictable control flow, useful comments, and tests that document expected behavior.
