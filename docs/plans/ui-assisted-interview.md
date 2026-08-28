# Plan — the assisted interview

**Date:** 2026-08-27
**Status:** in-progress
**Decision owner:** Richard, 2026-08-27

## The problem this solves

The in-app interview asks a gym owner "What the business is, who it serves, and what makes it
different from the one down the road" and gives them an empty box. A blind critic named the failure
exactly: *"a big empty box under it, which is exactly the moment I freeze."* We removed the
terminal handoff in round 2 and left a blank page in its place. What lands in `brand.md` currently
depends on how good the operator is at writing about their own business cold, and most are not.

## The decision

The app offers **"Let my assistant interview me"** when an agent runtime is actually invocable on
the machine. It runs on the operator's own Claude Code or Codex subscription, on their tokens,
strictly on demand. When no runtime is present the affordance is not rendered and the plain
textarea is the whole path.

`claude` 2.1.246 is on PATH on the development machine; `codex` is not. Build for both, test
against what exists, and never render a control for a runtime that is not invocable.

## The architectural exception, stated honestly

`docs/architecture.md` currently says: *"The engine is model-free and deterministic; judgment,
interviews, synthesis, and writing happen in the business repository, driven by agents."*

That is no longer true without qualification, and the doc must be amended rather than quietly
contradicted. The new shape:

- The engine remains model-free **by default and in every existing command**.
- Exactly one module — `core/assist.py` — may invoke an external agent binary, and only when the
  operator explicitly asks for it. It is the documented seam, and nothing else in the engine calls
  a model.
- `dependencies = []` still holds. We shell out to a binary the operator already has; we never add
  an SDK, and we never make a network call ourselves.

If a reviewer cannot find that exception written down, the change is not finished.

## Surface

`mos assist status [--json]` — which runtimes are genuinely invocable, with the resolved path and
version. Presence on PATH is not enough; a runtime that cannot answer is not available.

`mos assist ask --field <name> [path] --transcript-json <json> [--json]` — one stateless turn.
The caller holds the conversation and passes it back each time; the engine keeps no session.
Returns either the assistant's next question, or a finished draft, on schema `mos.assist.v1`:

    { "schema": "mos.assist.v1", "ok": true, "field": "brand",
      "done": false, "question": "...", "turn": 2, "runtime": "claude" }
    { ... "done": true, "draft": "...", "turns_used": 4 }

Bound the interview: at most four questions before it must produce a draft. An assistant that
wanders is worse than a blank box.

## Grounding

The assistant must see what the brain already knows before it asks anything — the business name,
the mode, and the fields already answered, straight from `mos context show`. Generic questions are
the failure mode here; a gym owner who has already said what they sell should never be asked again.

## Non-negotiable rules

**Security.** Fixed argv lists, never a shell, `shutil.which` guarded. Operator text and model text
are passed as arguments or via a file the CLI writes itself — never interpolated into a command
string. Enforce a wall-clock timeout and a maximum transcript size, and fail closed.

**Model output is untrusted input.** It is data, not instruction. It reaches the DOM as text, is
never interpolated as markup, and is never executed. It is also never written to disk by itself:
the draft lands in the textarea, the operator reads it, and `mos context set` writes it under the
existing `--plan`/`--yes` gating. Prompt-injected content in a draft must not be able to reach a
command, a path, or a file.

**The UI still writes nothing.** Unchanged from every previous round.

**Cost honesty, and no polling.** This runs on the operator's own subscription and spends their
tokens. Say so, in the interface, where they choose it. It fires only on an explicit click — never
on page load, never on a timer, never speculatively in the background. Richard's standing
preference is on-demand only, and this is the feature that would be most tempting to violate it.

**Graceful absence.** No runtime means no control — not a disabled button, not an error. The
plain path must remain complete on its own.

## Done means

- `mos assist status` truthfully reports what can actually answer, not what is merely on PATH.
- A full assisted interview runs end to end in a real browser and produces a draft the operator
  edits and saves, with `mos status` agreeing afterwards.
- With every runtime removed from PATH, the app renders no assistant control and the manual path
  still completes.
- The architecture doc states the exception plainly.
- No shell, no injection path from model output to execution, enforced by tests.
- Suite green (333+), ruff clean, `dependencies = []`.
