# Round 2 — accessibility audit (independent, fresh context)

**Date:** 2026-08-26
**Status:** open

Every item below was found by reading the shipped code, not screenshots. Line numbers are
from the files as audited; verify before trusting them, the files have since moved.

XSS: **clean**

## Contrast failures

- --ink-3 #77738a on --surface-3 #e9e6e0 (.mode__tag, styles.css:1013-1022, 11px) = 3.66:1 light / 3.86:1 dark — worst pair in the sheet, fails AA in both themes
- --accent #5b46e5 on color-mix(accent 16%, --accent-soft) (.mode input:checked + .mode__card .mode__tag, styles.css:1024-1027, 11px) = 4.17:1 light — selecting the recommended mode makes its own 'most people' badge fail AA
- --ink-3 on --accent-soft #efecff (.field__help inside .field--nested, styles.css:744-762 as used by index.html:206-209, 13px) = 3.93:1 light / 4.11:1 dark
- --ink-3 on --surface-2 #f2f0ec (.count__l styles.css:1242, .wizard__hint styles.css:731, .tree__count styles.css:1196) = 4.01:1 light / 4.28:1 dark
- --ink-3 on --bg #f7f6f3 (.cmd-item__cli styles.css:1630, .cmd-group__label styles.css:1589, .stepper__item styles.css:627, .boot__detail styles.css:338) = 4.22:1 light — passes in dark (4.90:1), fails in light
- #fff check glyph on --ok #4cc79a in dark (.runstep[data-state=done] .runstep__icon styles.css:1313, .citem[data-done=true] .citem__box styles.css:1539) = 2.11:1 — fails SC 1.4.11 (3:1 for meaningful graphics)
- #fff x glyph on --err #ff8b82 in dark (.runstep[data-state=failed] .runstep__icon styles.css:1324) = 2.27:1
- --accent-soft as the focus outline colour against --surface (.input:focus-visible / .select:focus-visible, styles.css:787-793) = 1.16:1 light / 1.11:1 dark — the declared focus indicator is invisible
- --ink-3 on --surface #ffffff (.card__sub, .field__help, .runstep__sub, .empty__body, .row__path, .citem__body) = 4.56:1 light / 4.58:1 dark — passes AA by 0.06, no margin left for any surface change
- --brand__sub --ink-3 over the 88%-opaque topbar (styles.css:259-263, 11.5px) = 4.52:1 light — passes by 0.02 only because the topbar is nearly opaque

## Defects

### [blocker] `app.js:1913`

Every `choices` arg renders a <select> whose displayed value and submitted value disagree. fieldFor sets `initial = argName === "path" ? App.path : argName === "runtime" ? "all" : ""` (1894) and seeds `cmd.values[argName] = initial` (1895). For `mode` (ARG_INFO.mode, choices in-house/agency/client) initial is "", no <option> matches, so the browser auto-selects the first option and the user sees "in-house" — while cmd.values.mode is "". argsFromForm (2013) drops empty strings, so the arg is never sent. If the server's spec lists `mode` as required, renderRunButtons (2027-2029) computes it as missing and both Preview and Apply stay disabled forever, with the select visibly filled in. The command cannot be run from the Commands view at all, and there is no error text explaining why.

**Fix:** When info.choices exists and initial is falsy, set `initial = info.choices[0]` before seeding cmd.values, or prepend a real empty <option value="">Choose…</option> so the visible state matches cmd.values. Add a change-listener sync on mount rather than relying on the seeded value.

### [blocker] `app.js:1942`

Required command arguments are invisible to assistive technology and the failure mode is a silent dead end. The only required indicator is `el("span", { text: " *", "aria-hidden": "true" })` — explicitly hidden from AT — and the control itself gets no `required` or `aria-required` attribute (1917-1926). makeRunButton then sets `button.disabled = true` (2069), which removes the button from the tab order entirely, and the explanatory "Fill in X first." text (2052-2062) is a plain <p class="field__help"> that is neither a live region nor referenced by aria-describedby. A screen-reader or keyboard-only user in the Commands view tabs through the form, finds no run button, and is never told a field is required or which one.

**Fix:** Set `required` (or aria-required="true") on the control when `(spec.required||[]).indexOf(argName) !== -1`, drop the aria-hidden from the asterisk or replace it with visible text, and switch the run buttons from `disabled` to `aria-disabled="true"` + a click handler that moves focus to the first missing field and announces the reason via announce().

### [blocker] `app.js:404`

Activating Refresh destroys the focused element and swaps the entire view with no announcement. The handler calls refresh(true) (2135-2141), which calls setView("boot"); setView line 374 runs `show($("btn-refresh"), onBrain)` with onBrain false, hiding the very button that currently holds focus. Focus falls to <body>, the dashboard is replaced by the boot spinner, and nothing is written to #live. The same pattern fires from the "Open this brain" button (723-727) and "Open the dashboard" (1308-1312), both of which call refresh(true) from inside a subtree that is then hidden. A keyboard user is dropped to the top of the document mid-task; a screen-reader user is given no signal that anything happened.

**Fix:** In refresh(showBoot), announce the transition ("Re-reading the folder") before setView, and after the promise resolves move focus deliberately — to #dash-title with tabIndex=-1 for the dashboard path, or to #boot-title on failure — rather than letting the focused node be hidden out from under the user.

### [major] `index.html:75`

role="tab" with no tablist. The two tab buttons (76-79) carry role="tab", aria-selected and aria-controls, but their parent is <nav class="tabs" aria-label="Sections">, whose implicit role is `navigation`. `tab` has `tablist` as a required context role, so this is invalid ARIA: the set relationship is lost (no "tab 1 of 2"), NVDA/JAWS will not reliably enter tab-widget mode, and aria-selected on an orphaned tab is undefined behaviour. The matching role="tabpanel" sections (270, 283) also have no tabindex, so the panel itself is never focusable after activation.

**Fix:** Put role="tablist" on the nav (it overrides the navigation role) or wrap the buttons in a <div role="tablist">, keep the aria-label on whichever element carries tablist, and add tabindex="0" to both tabpanel sections.

### [major] `app.js:568`

busy() sets `button.disabled = isBusy` on the button the user just activated. In Chrome, Firefox and Safari, disabling the focused element moves focus to <body>. This fires on every async action in the app — Continue on wizard step 1 (853), every hero action (1466), Apply (1502), and every Preview/Apply/Run in the Commands view (2077) — so a keyboard user loses their position on literally every operation, and busy(button,false) never restores focus. Combined with the fact that only a terse announce() ("Running status.") reaches #live, the user has no idea where they now are.

**Fix:** Use aria-disabled="true" plus a guard in the click handler instead of the disabled property, or capture document.activeElement before disabling and restore focus to the button in the same tick that re-enables it.

### [major] `index.html:302`

The toast is not a live region: `<div class="toast" id="toast" hidden>` has no role and no aria-live. toast() (app.js:89-97) sets textContent and unhides it, then hides it again after 2200ms. Nothing it says is ever announced — including the only error path in legacyCopy: `toast("Copy failed - select the text instead")` (app.js:121). That error is delivered by an unannounced, colour-neutral popup that auto-dismisses in 2.2 seconds, so a screen-reader user is told nothing and a low-vision user may miss it entirely. This is the clearest case in the app of an error that is not announced.

**Fix:** Add role="status" aria-live="polite" (or role="alert" for the failure case) to #toast, and route the copy-failure message through announce() as well so it lands in #live regardless of the toast timeout.

### [major] `index.html:241`

#preview-body and #apply-body (251) are declared aria-live="polite" but are used as full-page render targets. renderPlan (app.js:1088) and applyPlan's paint() (app.js:1119) both call fill(), which clears the node and re-appends an entire subtree — for a real onboard plan that is the counts block plus renderTree's hundreds of <li> rows. With the default aria-relevant="additions text", the whole tree is queued for announcement. paint() re-renders the same three-step list six times during apply, so the run list is read out in full six times over. This is unusable verbosity, and it is announcing structure rather than the state change that actually matters.

**Fix:** Remove aria-live from the container. Keep a small dedicated status element (or reuse #live) and announce only deltas — "Plan ready: 214 items would be created", "Checking the structure", "Failed: stopped before finishing" — from renderPlan and from each paint() transition.

### [major] `app.js:684`

Every keystroke in the folder field triggers a polite announcement. The input handler (747-750) calls probePath() on each `input` event; probePath writes `note("info","info",["Checking that folder..."])` into #where-readout synchronously (684) before the 320ms debounce, and #where-readout is aria-live="polite" (index.html:136). #where-readout is ALSO listed in the input's aria-describedby (index.html:132), so its content is announced a second time as the field's description. Typing a 40-character path produces 40 queued announcements plus the description re-read. The same double-duty applies to #name-readout (index.html:227 describedby + 230 aria-live) via onNameInput (770-789).

**Fix:** Only write the "Checking" note inside the debounced work callback, not on every keystroke; and stop pointing aria-describedby at a live region — use a separate static help id for the description and let the live region carry only the result.

### [major] `styles.css:787`

.input:focus-visible / .select:focus-visible / .textarea:focus-visible override the global focus ring (206-210, a 2px --accent outline at 2px offset) with `outline: 2px solid var(--accent-soft); outline-offset: 0`. --accent-soft against --surface is 1.16:1 in light and 1.11:1 in dark — the declared indicator is invisible. The only remaining cue is the 1px border switching from --line-strong to --accent, which is a 1px colour-only change. Every text input in the app (wizard path, business name, agency name, and every generated command field) is affected.

**Fix:** Drop the override, or keep the soft ring as a second layer while restoring a real one: `outline: 2px solid var(--accent); outline-offset: 0; box-shadow: 0 0 0 4px var(--accent-soft)`.

### [major] `styles.css:1313`

The success and failure glyphs are invisible in dark mode. `.runstep[data-state="done"] .runstep__icon` hard-codes `color: #fff` on `background: var(--ok)`, which in the dark palette is #4cc79a — 2.11:1. The same hard-coded #fff appears at 1324 on --err #ff8b82 (2.27:1) and at 1539 for `.citem[data-done="true"] .citem__box` on --ok. These are meaningful non-text graphics carrying the done/failed state and need 3:1 under SC 1.4.11. The literal #fff also bypasses the theme system entirely — every other on-accent surface uses --accent-ink, which correctly flips to #14111f in dark.

**Fix:** Replace `color: #fff` with a theme token in all three rules (add --ok-ink / --err-ink alongside --accent-ink, set to #ffffff in light and to the dark surface colour in dark), so the glyph inverts with the palette.

### [major] `app.js:1796`

The generated "Re-check" button has no accessible name below 640px. It is built as `class: "btn btn--ghost btn--icon"` with children [icon("refresh"), <span>Re-check</span>] (1804) and no title or aria-label. styles.css:1816 sets `.btn--icon span { display: none }` inside the 640px breakpoint, which removes the span from the accessibility tree; the SVG is aria-hidden="true" (app.js:58). The result is a focusable <button> with an empty accessible name — SC 4.1.2. The hand-written #btn-refresh in index.html only escapes this because it carries title="Re-read the folder" (index.html:85), which this one does not.

**Fix:** Add `title: "Re-check"` / aria-label to the generated button, or better, change the mobile rule to visually hide the span (.sr-only technique) rather than display:none so the name survives at every width.

### [major] `app.js:2166`

fatal() is completely silent to assistive technology. It rewrites #boot-title, #boot-body and #boot-detail with textContent, injects a Try again button, and calls setView("boot") — but #boot is not a live region, no announce() is called, and focus is never moved. When the local app stops answering mid-session (the exact case this handles, reached from refresh() at 2146 and boot() at 2215), a screen-reader user is left on a page whose entire contents were swapped for an error with zero notification, and a keyboard user must tab from <body> to find the Try again button.

**Fix:** Call announce(title + ". " + body) inside fatal(), and move focus to #boot-title with tabIndex=-1 after setView, matching what goStep() already does correctly at 805-810.

### [major] `app.js:1944`

Help text in the generated command form is not programmatically associated with its control. `info.help ? el("p", { class: "field__help", text: info.help }) : null` creates a bare <p> with no id, and the control (1917-1926) gets no aria-describedby. So the guidance that actually matters — ARG_INFO.hq's "Client mode only: adds a row to that agency's client list", ARG_INFO.agency's "Recorded when the mode is client" — is never read when the field receives focus. The hand-written wizard fields do this correctly (index.html:132, 211), which makes the omission in the generated path a clear regression rather than an oversight of convention.

**Fix:** Give the help paragraph `id: id + "-help"` and add `"aria-describedby": info.help ? id + "-help" : null` to the control attrs.

### [major] `app.js:2128`

Async command results are announced without content. renderCommandResult fills #cmd-result (not a live region) and then announces only "Command finished." or "Command needs attention." The findings themselves — the error messages, the paths, the change list — are rendered visually and never announced, and focus is not moved to the result. A screen-reader user is told a binary outcome and must then hunt back through the document to find out what it was. The same applies to renderDashboard, which refresh(false) re-renders after every mutating Apply (2086, 1505) with no announcement at all.

**Fix:** Announce a summary that carries the actual state (e.g. `plural(errors.length,"problem") + " found: " + errors[0].message`), and move focus to the result card heading with tabIndex=-1 so the user lands on the output they just asked for.

### [major] `app.js:845`

The Continue button is silently disabled with no stated reason. On step 2, `next.disabled = !wiz.mode || (wiz.mode === "client" && !wizAgency())`; on step 3, `!wizName()`; on step 4, `blocked` when the plan has no changes. HINTS[3] is the empty string (818) and HINTS[2] talks about something else entirely. Because `disabled` removes the button from the tab order, a keyboard user on step 3 tabs from the name field straight past the footer and finds nothing — there is no error message, no aria-describedby, and nothing in #live. This is SC 3.3.1/3.3.3 (error identification and suggestion) failing on the primary conversion path.

**Fix:** Switch to aria-disabled plus a click handler that focuses the offending field and announces why, and put the actual reason into #wizard-hint ("Enter a business name to continue") instead of leaving HINTS[3] empty.

### [major] `app.js:1502`

applyBar destroys the focused button and gives back nothing. `busy(apply, true, "Applying")` disables the button under focus (sending focus to <body>), then the resolution handler calls `fill(panel, ...)` (1504), which removes the apply button from the DOM entirely, then `refresh(false)` re-renders the dashboard beneath. There is no announce() anywhere in this path, so the user who just wrote files to disk from the keyboard gets no confirmation, no focus anchor, and no way back to where they were.

**Fix:** Announce the outcome from the .then, and after replacing the panel move focus to the new result card (tabIndex=-1 on its first heading) instead of leaving activeElement on <body>.

### [minor] `styles.css:836`

Checkbox targets fall short of the 24x24 CSS px minimum (SC 2.5.8). `.check` has no padding and a 13.5px font against body line-height 1.55, giving a label box of ~20.9px tall; the input itself is the ~13px browser default (844-847). These are laid out by `.flags` as a wrapping flex row with `gap: 16px` (1651-1656), so adjacent flag targets are 16px apart and the 24px-diameter spacing exception does not rescue them. Every boolean CLI flag in the Commands view (strict, grep, pending, no-ui) is affected.

**Fix:** Add vertical padding to `.check` (e.g. `padding: 4px 0`) or set `min-height: 24px; align-items: center`, and raise the `.flags` gap to at least 24px.

### [minor] `styles.css:1665`

Under prefers-reduced-motion the indeterminate progress bar becomes a misleading determinate one. The reduced-motion block (1879-1893) forces `animation-duration: 0.001ms; animation-iteration-count: 1` on everything and then re-enables only .spinner, .runstep__icon and .btn__spin (1888-1892). `.progress__bar` is not in that list, so its `slide` keyframe completes instantly and, with fill-mode none, the element reverts to its static state: a 34%-wide accent bar sitting at the left edge, unmoving, for the whole duration of the command. It reads as "34% complete" and never changes.

**Fix:** Either add `.progress` to the reduced-motion exception list with a slow non-translating alternative, or set `.progress__bar { width: 100%; opacity: .4 }` inside the reduced-motion block so it reads as an indeterminate wash rather than a stalled percentage.

### [minor] `styles.css:1158`

Three scrollable regions have no keyboard access path: `.tree` (max-height 19rem, overflow auto), `.changes` (1705-1711, max-height 15rem) and `.raw__pre` (1742-1752, max-height 22rem). None carries tabindex="0" and none contains a focusable child in the common case — the tree's only focusable nodes are the two collapsed .claude/.agents <summary> elements, and .changes/.raw__pre contain no interactive content at all. On any engine that has not shipped automatic focusability for scroll containers, a keyboard user cannot scroll them and the overflowed content is unreachable (SC 2.1.1).

**Fix:** Add `tabindex="0"` and an accessible name (role="region" aria-label="Planned files" / "Changes" / "Raw result") to the three scroll containers where they are constructed — app.js:1056, 473-479, 495.

### [minor] `styles.css:664`

Stepper completion state is conveyed by fill colour alone (SC 1.4.1). `[data-state="done"] .stepper__dot` differs from the default todo dot only in border-color/background/color — the digit stays visible in both, there is no tick, no strikethrough, no shape change. goStep sets aria-current="step" for the current item only (app.js:799), so "which steps are behind me" has no non-visual and no non-colour representation. Below 640px `.stepper__label { display: none }` (1837) removes the step names from the accessibility tree as well, leaving bare digits.

**Fix:** Swap the digit for a tick glyph (or add a ::after checkmark) on [data-state="done"], and give each stepper__item an sr-only status word so the state survives both the colour and the mobile label removal.

### [minor] `app.js:546`

Result sections are visual headings with no heading semantics (SC 1.3.1). "Worth knowing" / "What is wrong" (546), "Would change" / "Changed" (551), "Changes" (554), "Next" (559), "Then, inside that folder" (1075) and "It still needs to hear from you" (1260) are all rendered as `<p class="subhead">`, styled at 11.5px/620-weight/uppercase/0.07em — unmistakably section headers. Screen-reader users cannot navigate the result card by heading, and in a long doctor result that is the only practical way through it. The same applies to `.cmd-group__label` (1845), which heads each group inside the Commands nav.

**Fix:** Emit these as `el("h3", { class: "subhead", ... })` (they sit under the h2 card titles at 1656/1711/1786/1991, so the level is correct), and make .cmd-group__label an h3 inside the nav.

### [minor] `app.js:757`

Revealing the agency field is never announced. The change handler runs `show($("agency-field"), input.value === "client")`, which un-hides a container holding a newly-required text input. #agency-field is not a live region, the fieldset has no aria-describedby or aria-controls pointing at it, and updateFoot() silently disables Continue as a result (845). The comment above it (755-756) correctly justifies not stealing focus, but nothing was put in place of the focus move: a screen-reader user picks "This one is for a client of an agency", hears nothing new, and finds Continue has vanished from the tab order.

**Fix:** Add `aria-controls="agency-field"` to the client radio and call announce("Agency name required.") when the field is revealed — keeping the no-focus-steal behaviour the comment argues for.

### [minor] `app.js:516`

Malformed envelopes crash the renderer and strand the UI in its busy state. resultCard does `envelope.findings.filter(...)` with no guard (516, 520), and `envelope.changes.length` at 550; healthGrid does `status.findings.filter` (1605) and findingsCard `status.findings.length` (1809). Any envelope missing one of those keys throws inside the promise handler, so `busy(button, false)` and `fill(button, [label])` (2080-2081) never run — the button stays disabled and spinning forever, with no error surfaced anywhere. The `run()` wrapper (148-173) is careful to always resolve, which makes this the one unhandled failure mode left.

**Fix:** Default the arrays at the top of resultCard/healthGrid (`var findings = (envelope.findings || []); var changes = (envelope.changes || []);`) and wrap the .then bodies in try/catch that falls back to the transport error note.

### [minor] `styles.css:1896`

.pill--path truncates the repository path with an ellipsis (overflow:hidden + text-overflow:ellipsis, inheriting white-space:nowrap from .pill at 474) and the element that uses it — `el("span", { class: "pill pill--path", text: envelope.repo })` at app.js:1054 — is a non-interactive <span> with no title attribute. On a long path the user is shown a truncated destination on the exact screen where they are asked to approve writing files to it, with no tooltip, no wrap and no way to reveal the rest. The `.chip` next to it gets this right (app.js:654 sets title).

**Fix:** Add `title: envelope.repo` at app.js:1054, or drop nowrap for this variant and let the path wrap with overflow-wrap: anywhere, as .row__path already does.

### [minor] `styles.css:136`

`ul, ol { list-style: none }` with no compensating role="list" strips list semantics in Safari/VoiceOver — the "1 of 5" / "4 items" counts are lost. This hits the stepper (index.html:106), findingRows (app.js:424), changesList (473), runtimeCard's rows (1725) and every level of renderTree (936).

**Fix:** Add `role="list"` to those constructors, or scope the reset so it does not apply to lists that carry semantics.

### [minor] `app.js:11`

False claim in the file header comment: "Everything rendered here comes out of a real envelope. Nothing is invented." Roughly a third of the user-facing prose in this app is hard-coded here and never appears in any envelope — CONTEXT_INFO (181-206), COMMAND_INFO (208-305), ARG_INFO (313-335), the APPLY_STEPS captions (1093-1101), the tile bodies in healthGrid (1615-1639) and, most consequentially, heroPlan (1511-1589), which writes diagnostic sentences like "Your assistants cannot see the latest skills." and "Some files are not where the schema expects them." from a bare next_action id. The adjacent CSP claim on the same comment block is accurate (server.py:51 sends script-src 'self'), which makes the invented-content claim read as verified when it is not.

**Fix:** Reword to what is actually true — "no envelope value is ever interpolated as markup; explanatory copy is authored here and keyed off envelope ids" — so the next reader does not trust heroPlan's sentences as server-reported facts.

### [minor] `styles.css:1879`

The prefers-reduced-motion block re-enables three infinite rotations with !important (1888-1892): .spinner, .runstep[data-state="running"] .runstep__icon and .btn__spin all keep spinning at 1.4s forever. During applyPlan a user who has explicitly requested reduced motion sees a rotating step icon plus a rotating button spinner simultaneously, indefinitely, with no static alternative offered. Slowing an infinite rotation is not the same as reducing it.

**Fix:** Replace the rotation with a non-motion busy cue under reduced motion — an opacity pulse at low amplitude, or a static ring plus the existing aria-busy and #live text, which already carry the state.

### [minor] `styles.css:1201`

Collapsed tree disclosure targets are ~23px tall, just under the 24px SC 2.5.8 minimum, and they sit adjacent to each other. `.tree` sets font-size 12.5px with line-height 1.85 (1162-1164) giving a 23.1px summary line box with no padding. renderTree collapses exactly the .claude and .agents directories (app.js:940) and sorts dir names (932), so those two <summary> targets are always rendered as immediate stacked siblings with zero gap — the spacing exception does not apply.

**Fix:** Add `padding: 2px 0` to `.tree details > summary` (or set min-height: 24px), which also improves the pointer target on touch.

## Auditor's verdict

Not shippable as an accessible UI. XSS is genuinely clean — no innerHTML, insertAdjacentHTML, outerHTML, document.write, eval, Function, DOMParser or srcdoc anywhere in the three files; every envelope value reaches the DOM through el()'s `text:` (textContent) or add()'s createTextNode, and no envelope value ever reaches setAttribute (icon() interpolates only literal names into `use[href]`). The CSP comment at index.html:13-14 is TRUE — server.py:51 sends `script-src 'self'` (it also sends `style-src 'unsafe-inline'`, which is what makes app.js's inline `style:` attributes at 1508/1764/2002 legal). The comment at app.js:11 ("Everything rendered here comes out of a real envelope. Nothing is invented.") is FALSE — CONTEXT_INFO, COMMAND_INFO, ARG_INFO and the whole of heroPlan() (1511-1589) invent user-facing prose, including diagnostic sentences like "Your assistants cannot see the latest skills." Keyboard: no focus trap, and the mode group IS a correct native radiogroup (fieldset + same-name radios at index.html:148-202 gives arrow keys and roving tabindex for free; the visually-hidden inputs at styles.css:946-951 stay focusable with opacity:0, and 970 gives them a real focus ring) — that part is right. Everything else about focus is not: every async button disables itself under focus, and three separate flows destroy the focused element and swap the view with no announcement. Screen reader: landmarks are correct, but role="tab" has no tablist, required fields are invisible to AT, the toast is not a live region, and the two big wizard containers are aria-live regions that get whole subtrees injected into them. Contrast: the accent button passes in both themes; --ink-3 fails against every surface except --surface, and the dark-mode success/failure glyphs sit at ~2.1:1.
