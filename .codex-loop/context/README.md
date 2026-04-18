# Context Engine

This directory stores compressed context packets for long-running harness runs.

- `current-state.md`: expanded working context built from repo state
- `handoff.md`: short packet safe to replay into the next iteration
- `durable.json`: long-lived facts, constraints, style rules, and contracts
- `open-questions.json`: unresolved questions that still matter
- `events.jsonl`: append-only refresh log for debugging context drift
