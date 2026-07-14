---
name: mos-setup
description: Create a new marketing-os business brain or safely complete its initial context and runtime wiring.
---

# Setup

Create an agent-ready marketing brain without inventing folders or overwriting business truth.

## Detect

Run `mos status . --json` first when the current directory may already be a repository.

- If it is ready or incomplete, continue in place.
- If it is empty, collect the business name and proposed destination.
- If it is a non-empty directory without a marketing-os identity, do not adopt or migrate it.
  Propose a new empty destination.

## Plan before writing

Preview setup with:

```bash
mos setup "<path>" --name "<business name>" --runtime all --plan --json
```

Explain the destination and proposed changes. Ask for approval before applying:

```bash
mos setup "<path>" --name "<business name>" --runtime all --yes --json
```

## Establish minimum context

After scaffolding, gather these four inputs conversationally:

1. What the business is and wants to be known for.
2. Who the primary audience is and what they are trying to change.
3. The primary offer: name, promise, mechanism, price or commercial model, and next step.
4. How the business should sound, including representative examples and language to avoid.

Propose the exact edits before saving. After approval:

- update `business/brand/brand.md` and `business/brand/voice.md`;
- update `business/audience/primary.md`;
- create `business/offers/<offer-slug>/offer.md` using a lowercase hyphenated slug;
- update `CONTEXT.md` with the current focus and desired outcome.

Never collect secrets, credentials, raw customer exports, or private account data into tracked
files. Never replace a non-placeholder business file without discussing the change.

## Verify

Run:

```bash
mos validate . --json
mos status . --json
mos doctor . --json
```

Finish with the business outcome, context gaps, runtime readiness, and one next action.
