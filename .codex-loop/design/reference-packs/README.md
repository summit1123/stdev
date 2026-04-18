# Design Reference Packs

These packs are reusable visual reference families for SummitHarness.

Use them when a project needs stronger visual guidance than a raw `Preset` can provide.
A `Preset` defines the broad operating lane. A `Reference-Pack` defines the concrete design bias, anti-patterns, and layout behavior that Ralph should follow.

## How to choose

- Start with the mode in `.codex-loop/config.json`.
- Choose a `Preset` in `.codex-loop/design/DESIGN.md`.
- Choose one `Reference-Pack` that matches the product or document.
- If no pack fits cleanly, duplicate the closest one into the project-local `.codex-loop/design/reference-packs/` folder and edit it there.

## Families

### Document / reviewer-facing
- `editorial-signal`: dense authored documents, proposals, PRDs, and evidence-heavy submissions.
- `analyst-workbench`: comparative, research-heavy, and reviewer-driven information layouts.

### Product / citizen / consumer
- `citizen-service`: public-service and delegation flows that need warmth, clarity, and predictable steps.
- `consumer-trust`: consumer apps that must feel polished without falling into generic AI-app tropes.

### Product / developer / operator
- `security-console`: security, guardrail, audit, and runtime evidence products.
- `devtool-minimal`: compact builder tools, CI dashboards, and internal control panels.

### Impeccable-inspired
Inspired by [pbakaus/impeccable](https://github.com/pbakaus/impeccable), these packs emphasize anti-pattern avoidance, stronger typography and spacing discipline, and deliberate visual polish.

- `impeccable-operator`: high-accountability dashboards and consoles.
- `impeccable-consumer`: consumer-facing flows with cleaner UX writing and calmer polish.
- `impeccable-responsive`: product surfaces that must stay coherent across breakpoints and states.
