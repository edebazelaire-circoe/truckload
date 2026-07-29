# Question Protocol

Use this protocol whenever the session reveals non-compliant or ambiguous implementation choices.

## A) Non-compliant code in scope

Ask in this format:

1. `Issue`: concise statement of what breaks current rules.
2. `Conflict`: why it conflicts with current architecture/workflow.
3. `Recommended option (best)`: concrete fix and rationale.
4. `Alternative option`: acceptable fallback and tradeoff.
5. `Decision requested`: explicit user confirmation.

## B) New logic introduction

Always announce:

`IMPLEMENTING NEW LOGIC - <name>: <short description>`

Then ask:
- whether equivalent logic already exists elsewhere
- whether to reuse/refactor instead of adding new path

Proceed only after user response or explicit authorization to continue with best assumption.

### Observability exception

Standard LogBroker instrumentation does **not** require a separate user confirmation when it directly supports an already-requested implementation or fix.

The agent may add without pausing:
- durable LogBroker events for expected workflow boundaries
- `capture_exception(...)` calls in non-rethrowing `except` blocks
- registered error-code usage for failure paths already in scope
- CLI log checks and test assertions that verify expected events
- temporary `TEMP:*` probes or `debug_checkpoint(...)` entries inside an active `/debug` session, as long as they are tied to a hypothesis and cleaned up before closure

The agent must still use the new-logic or temporary-behavior protocol before adding:
- a new permanent LogBroker channel
- a new fallback, mock, compatibility alias, or alternate business path
- a new logging subsystem outside LogBroker
- a durable behavior change that affects product/runtime decisions rather than observability only

## C) Temporary behavior

Before adding temporary behavior, ask:
- expected lifetime
- exit/removal condition
- where to track legacy note
