---
name: debug
description: use this skill when implementing, refactoring, testing, or debugging Symphonia code that should leave readable LogBroker evidence. Trigger it when the user asks for debug instrumentation, runtime diagnosis, agent-readable logs, human-in-the-loop debugging, failure investigation, trace review, validation evidence, or guidance on how to use the LogBroker. The skill explains when to add normal logs, how to structure temporary diagnostic logs, how to inspect logs after tests or manual runs, and how to convert findings into fixes without turning logs into hidden memory or source-of-truth state.
---

# Debug

## Purpose

Use this skill to make debugging observable, repeatable, and useful to both Humans and Work Agents. The LogBroker is the central entry point for implementation logs, runtime errors, debug probes, validation traces, and agent-readable troubleshooting evidence.

The goal is not to log everything. The goal is to leave enough structured evidence that a later agent can answer: what happened, where, with which context, what was expected, what failed, and what should be checked next.

## Core Rules

1. Add normal logs while implementing important flows, not only after failures.
2. Prefer structured LogBroker calls over scattered console prints.
3. Keep source records authoritative. Logs are evidence, not product state.
4. Do not log secrets, credentials, raw private user content, full prompts, or unrestricted database results.
5. Label temporary diagnostic logs clearly and remove or downgrade them before completion.
6. After a failing test, manual run, or human-in-the-loop report, inspect relevant LogBroker entries before guessing.
7. Summarize log findings in the task output or validation notes.

## When To Add Normal Logs

Add stable, regular logs for events that help explain product behavior later:

- entering or completing a user-visible workflow;
- selecting a route, adapter, repository, task, or source;
- rejecting input with a validation reason;
- crossing a system boundary, such as UI to runtime, runtime to GIC, or DSA to source;
- producing a structured answer, classification, trace, event, or task-state transition;
- catching an exception or recovering from a degraded dependency;
- executing a guarded operation request or refusing one.

Do not add routine logs inside tight per-frame loops, hot rendering paths, or high-frequency polling unless sampling or debug gating is explicit.

## Log Levels

Use these meanings consistently:

- `Debug`: temporary or developer-only detail for diagnosis. Remove, gate, or downgrade before finishing unless it remains useful.
- `Info`: normal lifecycle or routing evidence. Safe to keep.
- `Warn`: unexpected but recoverable state, fallback, stale source, missing optional dependency, or ambiguous input.
- `Error`: failed operation requiring repair, user-facing failure, invalid invariant, exception, or corrupted state.

## Minimum Log Shape

Every LogBroker entry should include:

```text
category: stable area such as assistant.runtime, gic.query, ui.home_pa, dsa.docs, task.orchestrator
level: Debug | Info | Warn | Error
event: short stable machine-readable event name
message: one human-readable sentence
context: small structured values needed to diagnose the event
correlation_id: request/run/thread/task id when available
actor: User, Personal Assistant, Work Agent, system service, or unknown when not available
source_ref: file/path/task/thread/source id when available
```

## Suggested Event Names

Use lowercase dot-separated event names:

```text
assistant.message.received
assistant.response.generated
assistant.boundary.denied
assistant.memory.loaded
gic.query.received
gic.source.selected
gic.answer.returned
gic.intake.classified
dsa.lookup.empty
dsa.lookup.ambiguous
ui.panel.rendered
task.state.changed
validation.failed
validation.passed
guarded_operation.requested
```

## Debug Workflow

When diagnosing a bug or behavior mismatch:

1. Reproduce the issue with the smallest path available.
2. Add targeted temporary LogBroker probes around the suspected branch.
3. Include correlation ids so UI, runtime, adapter, and validation logs can be joined.
4. Run the relevant test or manual path.
5. Inspect LogBroker output before changing logic.
6. State the observed log facts in the task notes.
7. Fix the logic.
8. Keep stable Info/Warn/Error logs that document useful behavior.
9. Remove noisy temporary Debug probes or guard them behind debug mode.
10. Add or update regression tests using the discovered condition.

## Human-In-The-Loop Debugging

When the user must run the app or provide visual/manual feedback:

- add a small set of clear logs before asking for the run;
- tell the user which action to perform and which logs matter;
- after the user returns evidence, interpret the LogBroker entries first;
- do not ask the user to infer internal state manually when a log can record it.

## Completion Checklist

Before marking a coding task complete:

- stable workflow logs exist for important new behavior;
- temporary probes are removed, downgraded, or debug-gated;
- no sensitive data is logged;
- failures include actionable context;
- task output mentions what LogBroker evidence was checked or added;
- tests cover at least one important logged branch when feasible.

## Reference

For the project-level policy, read `references/logbroker-usage.md` when the task asks for detailed LogBroker guidance or when adding a new subsystem logging pattern.
