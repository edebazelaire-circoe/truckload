# LogBroker Usage Reference

## Intent

LogBroker centralizes runtime logs, validation evidence, and debug observations so Humans and Work Agents can inspect behavior after a test, manual app run, or implementation pass.

It should be used as a regular engineering habit, not only as an emergency debugging tool.

## Stable Logs vs Temporary Probes

Stable logs are part of the product's observability contract. Keep them when they explain lifecycle, routing, validation, access decisions, source lookups, state changes, or recoverable failures.

Temporary probes are diagnostic scaffolding. Add them to understand a branch, then remove, downgrade, or guard them before completion.

## Privacy and Safety

Never log secrets, credentials, tokens, full raw prompts, full private conversations, unrestricted database rows, or source content that the actor may not be allowed to see. Prefer identifiers, counts, labels, and redacted summaries.

## Agent Behavior

A Work Agent should use LogBroker as evidence. After failures, it should inspect logs and summarize observed facts before editing more code. If logs are missing, it should add narrow instrumentation and rerun validation rather than guessing.

## Good Example

```text
category: gic.query
level: Info
event: gic.answer.returned
message: returned sourced knowledge answer
context:
  query_kind: source_lookup
  source_count: 2
  confidence: high
  freshness: index_only
  gaps_count: 0
correlation_id: req-123
actor: pa:current-user
```

## Bad Example

```text
user asked huge raw message: <entire private content>
```

This leaks content, has no event name, no category, no correlation id, and no structured diagnosis value.
