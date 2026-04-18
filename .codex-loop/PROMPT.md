# Stable Loop Prompt

You are building a real product or document package, not a demo stub.

Every iteration should leave the repo in a more truthful state:

- sharpen the PRD when the brief is vague
- keep the active task state accurate
- refresh the compressed handoff when repo state changes
- make concrete progress in code, design specs, tests, assets, or docs
- prefer vertical slices over disconnected fragments
- keep outputs believable, grounded, and reviewer-credible

Respect the current operating contract:

- read `.codex-loop/QUALITY_BARS.md` and treat the active quality profile as a hard completion gate
- read `.codex-loop/design/DESIGN.md` and treat the design contract as a hard style and layout gate
- read the selected file under `.codex-loop/design/reference-packs/` and treat it as the active visual reference family
- read `.codex-loop/modes/<active-mode>.md` and obey that mode's source of truth
- do not declare completion until every MUST item in the active quality profile is satisfied

When the goal is proposal or submission work:

- the Markdown source is the source of truth
- PDF is packaging, not the place where quality suddenly appears
- add evidence, tables, comparisons, and workflow structure in source form first
- do not let decorative layout hide thin thinking
- write for a real reviewer, not for an assistant transcript

When the product has a UI:

- define the user flow before polishing surfaces
- keep spacing, hierarchy, and copy intentional
- use a coherent visual system with an explicit reference pack plus approved assets or references
- avoid ornamental noise, random cards, and empty accent shapes
- if the design still feels generic, improve the design inputs before polishing the code
- verify behavior in the running app once a UI exists

When backend or AI work is involved:

- define contracts first
- handle failure states
- record assumptions in the task spec or PRD
- do not silently invent critical business rules
