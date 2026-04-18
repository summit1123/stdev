# Mode Contract: PRD

Use this mode when locking requirements, users, constraints, and the executable task graph before build work.

## Source of truth

- `.codex-loop/prd/PRD.md`
- `.codex-loop/prd/SUMMARY.md`
- `.codex-loop/tasks.json`
- `.codex-loop/tasks/TASK-*.json`

## Completion bar

- The PRD names the user, workflow, scope, constraints, and non-goals.
- Acceptance criteria are concrete enough to build and verify.
- Tasks represent the real remaining work with one clearly runnable next task.

## Fail when

- The PRD is still brainstorming instead of a build contract.
- The task graph hides missing work.
- Requirements are vague, contradictory, or untestable.
