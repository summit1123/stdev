# .codex-loop

This directory is the project-owned runtime state for SummitHarness.

- `prd/`: the brief the harness must respect
- `tasks.json` and `tasks/`: the implementation graph
- `PROMPT.md`: stable instruction block
- `STEERING.md`: urgent course corrections
- `context/`: compressed handoff packets and durable facts
- `assets/registry.json`: approved/reference design assets
- `preflight/`: environment and toolchain checks
- `logs/`, `history/`, `reviews/`, `evals/`: run records and goal-evaluation traces
- `ralph-loop.json`: state for the Stop-hook self-loop mode

The plugin is reusable. This directory is where the project becomes yours.
