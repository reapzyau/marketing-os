# Round 2 — what the blind critics and the auditor found

**Date:** 2026-08-26
**Status:** in-progress
**Round 1 result:** 12 of 14 blind votes ours. Swept mode-choice, preview, dashboard, navigation,
commands. Split on first-screen and mobile — both splits lost the same vote, the non-technical
operator. The design director picked ours 7 for 7.

Read this with `docs/plans/ui-app.md`, which still holds the hard constraints. Nothing here
relaxes them: stdlib only, vanilla HTML/CSS/JS, no framework, no build step, no external request,
`dependencies = []`, the UI never writes a file itself.

---

## 1. Blockers — these are broken, not imperfect

**1.1 Commands with a `choices` argument cannot be run at all.** `app.js` `fieldFor()` sets
`initial = argName === "path" ? App.path : argName === "runtime" ? "all" : ""`. For `mode`, initial
is `""`, no `<option>` matches, so the browser selects the first option and the user *sees*
"in-house" while `cmd.values.mode` stays `""`. `argsFromForm` drops empty strings, the arg is never
sent, and because the server's spec lists it required, Preview and Apply stay disabled forever with
the select visibly filled in. No error explains why. Fix by seeding from `info.choices[0]`, or by
prepending a real `<option value="">Choose…</option>` so what is shown and what is held agree.

**1.2 Required arguments are invisible to assistive technology and dead-end silently.** The only
required marker is a `*` span that is `aria-hidden="true"`; controls get no `required` or
`aria-required`; the run button uses `disabled`, which removes it from the tab order entirely; and
the "Fill in X first." text is neither a live region nor referenced by `aria-describedby`. A
keyboard user finds no run button and is never told why.

**1.3 Refresh destroys the focused element and swaps the view silently.** `refresh(true)` calls
`setView("boot")`, which hides the very button holding focus. Focus falls to `<body>`, the view is
replaced, and nothing reaches `#live`. Same pattern from "Open this brain" and "Open the dashboard".

---

## 2. Why we lost the two blind pairs

**2.1 First screen — the path is the whole problem.** The operator: *"that reads like an error
message, not a suggestion, and I'd close it before working out what a path is."* The suggested
folder was `/tmp/mos-e2e/...`; the director noted we congratulate the user with a green "Good spot."
for a default they never chose, pointing at a directory the OS wipes. Fix: default to a real,
human place under the user's home; describe it in human words with the technical path available but
demoted; never show `/mnt/c/...` debris in suggestion chips; and say in one line what the thing does
before asking for a decision.

**2.2 Mobile at 390px — the two choices cannot be seen together.** *"Each option is a 400px slab of
paragraph text... asking me to compare two options I can never see together is a worse phone failure
than B's blandness."* The director added that triple nesting plus a decorative icon rail crushes the
body to ~28 characters per line. Fix: at 390px each option is a headline plus one plain line, no
file paths, no icon rail, one inset level fewer — both options and the button on one screen.

---

## 3. Named gaps in the pairs we won

- **Filesystem paths leak into plain-language copy.** `business/clients/clients.md` mid-sentence on
  the mode screen, `business/offers/<offer-slug>/offer.md` under checklist rows, the black command
  box first in the eye-line on the preview step. Both critics flagged this on multiple screens; it
  is the single most repeated finding in the round. Every such path goes behind a "show the
  technical bit" disclosure, off by default.
- **The dashboard fails its own arithmetic.** A chip says "4 things it has not been told yet" above
  a checklist that says "1 of 6". Both numbers are true — `context.missing` counts 4 required
  fields, the checklist counts 6 documents — but a reader computes 6−1=5 and catches us lying. Put
  them on one denominator, or label them so plainly that they cannot be read as the same count.
- **The sticky header collides with the page.** Body copy ghosts through it, the "Your assistants"
  heading and a badge are sliced in half, and the page reads as a rendering fault before the user
  has started. Fix the z-index and scroll-padding.
- **The Commands tab has no result surface.** It stops dead at "Run it" with roughly 600px of empty
  canvas below, so the reader has no idea output is coming or where it will land. Reserve and label
  that region *before* the click.
- **The preview tree cannot be seen whole.** It opens mid-scroll on a clipped row and is cut off
  again at the bottom, inside a card that itself runs off the viewport. Nested scroll on the one
  screen whose job is "look this over" undercuts the honesty the copy claims.
- **The mode options are supported asymmetrically.** Only the middle option carries a delta
  callout, so the three cannot be compared on one axis, and the genuinely confusing third option —
  am I the agency or the client? — gets the thinnest explanation.

---

## 4. The hole both critics found independently

The dashboard's next action tells a non-technical person to *"open this folder in Claude Code or
Codex and run the mos-onboard skill"* and offers a "Copy the file path" button. The operator:
*"useless to someone who's never opened a terminal. It should just ask me the brand questions in
the app."*

`mos context show` and `mos context set` now exist for exactly this. Build the interview in the
app: one question per screen in plain language, the answer written through `mos context set` with
the same Preview/Apply gating as every other mutating command. The UI still never touches a file
directly. After each answer, re-read `mos status` so the dashboard's counts move on their own.

---

## 5. Accessibility — 28 defects, full detail in the audit

Highest value first: the invisible focus ring (`--accent-soft` at 1.16:1 — the declared indicator
cannot be seen); every async button disabling itself under focus, which drops the user to `<body>`
on every single operation; the toast that is not a live region, so the only copy-failure error in
the app is announced to nobody; `role="tab"` with no `tablist`; the two wizard containers declared
`aria-live` that get whole subtrees injected into them, so an apply reads the entire run list out
six times; and `--ink-3` failing AA against every surface but one.

Ten contrast pairs fail. Fix them at the token level, not per-rule, and re-check both palettes.

Also: `app.js`'s header comment claims "Everything rendered here comes out of a real envelope.
Nothing is invented." That is false — `CONTEXT_INFO`, `COMMAND_INFO`, `ARG_INFO` and all of
`heroPlan()` author user-facing prose locally. Reword it to what is true. A comment that overstates
its own guarantees is worse than no comment, because the next reader trusts it.

---

## 6. Done means

- `uv run pytest -q` green, `uv run ruff check .` clean, `dependencies = []`.
- Every allowlisted command, including every one with a `choices` argument, can actually be run
  from the Commands tab and shows its result.
- No raw filesystem path appears in default-visible plain-language copy anywhere.
- At 390px both mode options and the continue button are visible without scrolling.
- The brand questions can be answered inside the app, and the dashboard counts move afterwards.
- All three accessibility blockers closed and every contrast pair at AA in both palettes.
- Screens re-captured at 1440x900 and 390x844 for the next blind round.
