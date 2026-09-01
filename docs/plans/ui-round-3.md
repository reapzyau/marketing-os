# Round 3 — the scoreboard, one regression, and what closes it

**Date:** 2026-08-26
**Status:** in-progress

Round 3 result: 13 of 16 blind votes ours, swept 6 of 8 pairs. Same eight pairs, same bar images,
only our side changed, sides reshuffled.

| Screen | gym owner | design director | vs round 1 |
|---|---|---|---|
| First screen | BAR | OURS | still split |
| Mode choice | OURS | OURS | held |
| Preview before commit | BAR | BAR | **regressed — was 2/2 ours** |
| Dashboard | OURS | OURS | held |
| Navigating inside | OURS | OURS | held |
| Command + result | OURS | OURS | held |
| Mobile 390px | OURS | OURS | **fixed — was split** |
| Interview question | OURS | OURS | new, swept on debut |

---

## 1. The regression — caused by round 2's own fix

Round 1's critics said the preview tree opened mid-scroll inside a nested scroller. Round 2
removed the nested scroller. That made the card taller than the viewport, so the summary, the total
count and the approve/cancel actions now sit below the fold. Both critics, independently:

> "No commit point and no summary. It shows ~40 lines of tree with no target path, no total count,
> no progress, and nothing to approve or cancel — so the user learns that many files exist without
> learning what they are for or being given the decision the screen exists to serve."

> "No plain-English explanation and no action anywhere on screen — just an endless list of .gitkeep
> files that means nothing to a normal person, with no button to press or approve."

**What closes it.** The decision must be on screen with the evidence, always. Lead the card with a
plain-English summary — what is about to be created, where, and how many things — then the tree,
then a commit bar that stays reachable no matter how long the tree is. Neither a nested scroller
nor an unbounded card: the summary and the action are what must never scroll away.

**Signal-to-noise in the tree.** `.gitkeep` renders ten times at full weight while the half-dozen
documents that actually matter get no emphasis. Scaffolding should recede; the files a person will
open should lead.

---

## 2. The first screen — stop asking the question

The director scored ours ahead on every dimension the question named and still called it narrow,
because ours loses on time-to-touch. The operator was blunter: the first thing it asks is where a
folder should live, *"I don't know. I don't care. I own a gym."*

Better copy will not fix a screen whose first move is a decision the reader cannot make. **Make
step 1 a confirmation, not a decision.** The default is already chosen and stated in words; the
primary action is Continue; choosing somewhere else is a quiet secondary that reveals the options
only when asked for. One click, no filesystem reasoning, escape hatch intact.

**And there is a real bug here, found independently by both critics.** Neither chip renders as
selected, yet the green readout names a destination matching neither label:

> "two grey pills that don't look selected, then a green box telling me it's going in
> `mos-ui-root, in your home folder`, which is a mix of both options. So which one did I pick?"

> "The state readout contradicts its own controls."

Fix the selected state so the live option is unmistakable, and make the readout name exactly what
is selected. Never surface a repo slug — `mos-ui-root` — as a human-facing suggestion label; that
is the terminal's directory name leaking into consumer copy.

---

## 3. Named gaps worth taking

- **The mobile footer is an unreflowed desktop row.** "You can change this later by editing one
  file" wraps into a five-line ribbon crowding Continue — and both critics singled out *"editing
  one file"* as the one phrase on the screen that makes a non-technical reader think something
  technical is coming.
- **Green ticks on all three mode options read as "validated".** Success green on a static
  consequence label implies every option is pre-approved. Use a neutral treatment; keep green for
  state that has actually been checked.
- **"The brain" is never defined.** It is the headline noun on step 2 and the operator still does
  not know what it is. Do not rename it — it is the product's metaphor and it runs through the CLI,
  the skills and BRAIN.md. Define it once, in a clause, on first use.
- **The dashboard runs three competing status systems for one fact** — the header pill, the tiles,
  and the "0 of 4 required" badge — and a tile caption apologises for the duplication in copy
  ("Same count as the checklist below"). As the director put it, a designer explaining redundancy
  in body text is a decision that never got made. Delete two of the three.
- **"Answer" links on the checklist are grey text, not buttons**, sitting at the same altitude as a
  filled primary doing the same job. Neither reads as the intended path.
- **No sensor guards the no-paths rule.** The round 2 verifier flagged this: the contract tests
  cover CSP, markup sinks, ARIA and contrast, but nothing stops a filesystem path returning to
  default-visible copy. Add the sensor so the rule cannot regress silently.

---

## 4. Done means

- The preview step shows a plain-English summary and a reachable commit action regardless of tree
  length, with scaffolding de-emphasised.
- Step 1 requires no decision: default chosen, stated in words, one primary action.
- The selected chip is unmistakable and the readout matches it exactly. No repo slugs in copy.
- A contract test fails if a filesystem path appears in default-visible copy.
- Suite green (318+), ruff clean, `dependencies = []`, screens re-captured for round 4.
