---
name: mos-bet
description: Open, update, close, list, or narrate a falsifiable business bet stored as a dated decision artifact.
---

# Business bet

Treat a bet as a falsifiable operating choice with a deadline and a verdict, not a task or an
offer description. A bet is a dated decision artifact; there is no bet command.

## Inspect

Run:

```bash
mos status . --json
mos validate . --json
```

List existing bets by reading every `bet.md` under `business/decisions/` (glob
`business/decisions/**/bet.md`). Do not invent revenue, customer, proof, or financial facts.

## Open

Only after approval, write the bet as a schema-conformant dated artifact:

```
business/decisions/YYYY/MM/YYYY-MM-DD-<slug>/bet.md
```

Use today's date and a lowercase hyphenated slug. Record: hypothesis, stake, deadline, success
signal, failure signal, status (`open`), and an empty evidence log.

## Update and close

- Update: append dated observations to the evidence log; never rewrite the original hypothesis.
- Close: set status to `won`, `lost`, or `void`, add the verdict and what it teaches, and note
  any follow-on decision.

Propose the exact edit before writing. After any write, verify:

```bash
mos validate . --json
```

## Narrate

When asked how the bets stand, summarize each open bet's hypothesis, deadline, and leading
evidence, then the recently closed verdicts. Lead with what the operator should decide next.
