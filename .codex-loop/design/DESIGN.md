# Design Contract

Preset: product-ops
Reference-Pack: impeccable-consumer

## Goal Type

This file is the design source of truth for the current workspace.

- Use `document-editorial` for proposals, submissions, PRDs, and strategy docs.
- Use `product-ops` for actual software UI, dashboards, and agent control surfaces.
- Use `Reference-Pack` to point Ralph at a reusable visual family before you start polishing.

## Why This Exists

Without an explicit design contract, autonomous loops tend to converge on the same weak defaults: nested cards, decorative accents, vague hierarchy, and product screens that look like AI-generated scaffolding rather than something a team would ship.

The design contract exists to stop that drift early.

## Current Direction

- Build a real product workspace, not a pitch-deck page.
- Keep the first screen task-first: upload, verify text, choose mode, generate, review.
- Typography stays black-first and calm, but interaction states must feel product-grade.
- Use visuals only when they ground the diary, the generated media, or the next action.
- Every surface must answer a user question immediately: what goes in, what comes out, what happens next.

## Preferred References

- Family diary or scheduling products that feel trustworthy without infantilizing the user.
- Creative tooling surfaces where source material, output media, and control state coexist in one workspace.
- Dense but calm consumer software that uses a few strong surfaces instead of many weak cards.
- Approved screenshots, generated assets, and final captures should be registered in `.codex-loop/assets/registry.json`.

## Project-Specific Rules

- The first viewport must show the actual tool workspace, not a marketing hero.
- Use one main content canvas, one source column, and one inspector column on desktop.
- Keep copy short and operational. Avoid explanatory AI narration.
- Show scenario text, generated video, and mission loop as first-class outputs.
- Use accent colors only to separate flows: source, discovery, mission.
- Avoid giant empty gaps, floating pills, and tiled card spam.
- Child-facing warmth is acceptable, but the product must still feel serious and premium.

## Banned Patterns

- sparse pages with only a few boxes
- ornamental circles, pills, and empty accent shapes
- assistant-style narration
- screenshots without reviewer value
- fake product metrics or unsupported claims
- layout polish that tries to compensate for thin substance
