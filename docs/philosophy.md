# Philosophy

marketing-os is built on one split: the CLI owns facts, the agent owns judgment.
Everything else follows from keeping that line clean.

## The CLI does not call a model, with one named exception

`mos` reads and writes the filesystem, validates structure against a fixed schema, and wires
runtime skill copies. Every command that reads or changes a brain is deterministic: no model,
no randomness, the same repository in and the same structure out. The calendar is the one
qualifier — `mos think`, `mos ingest` and `mos context set` write into dated execution trees,
so they stamp today's date and name a different path tomorrow. Because none of it reasons, it
can be trusted as ground truth — an agent asks `mos status` what is real instead of guessing.

One command may call a model, and it is named here rather than left to be discovered.
`mos assist` may run an agent runtime the operator already installed, so the local browser app
(`mos ui`) can interview someone who freezes in front of an empty box. It is one module, it
fires only on an explicit request, it writes nothing, and it is documented in
[the architecture](architecture.md).

One more command is outside the determinism claim without going anywhere near a model:
`mos ui` starts that app and reports back the pid, port and URL it happened to get, which is
by definition not the same answer twice. Neither command touches a brain's content. Every
other command is model-free and repeatable, and a claim of determinism anywhere else in these
docs means exactly that.

This is why the CLI stays small. It does the things a language model is bad at,
which are the things a program is good at: checking whether a file exists, whether a
folder name matches a dated grammar, whether a skill copy is current. Facts, not opinions.

## The agent owns everything a model is good at

Interviews, judgment, synthesis, and writing belong to the agent. The CLI will not
draft an offer, pick a voice, or decide what the current priority is. It scaffolds the
empty rooms; the agent, working with the user, furnishes them. The bundled
skills, such as `mos-onboard`, `mos-start`, and `mos-help`, are the agent's side of the contract:
they read deterministic facts first, then apply judgment on top.

Neither side reaches into the other. The CLI never invents business content. The agent
never fabricates repository state it could have read from `mos status`.

## Three surfaces, one engine

There are three ways to reach that CLI, and only one implementation behind them. A terminal
runs `mos` directly. An agent runtime runs it through the bundled skills. The local browser
app (`mos ui`) runs it too — the page names one of twenty-one allowlisted commands plus a bag
of arguments, the server turns that into a real argv list, and the same parser and the same
handlers answer. The app shows the exact `mos …` line it built, every time.

That last part is the point. A browser client that reimplemented any of this would drift from
the CLI within a release, and the first person to notice would be someone whose dashboard
disagreed with their terminal about their own business. Making the app a client rather than a
second implementation is what keeps that from ever being possible.

## Grounding beats prompting

A generated repository is a brain made of markdown files. `business/` holds the sole
source of business truth. `knowledge/` holds immutable sources and the synthesized
pages built from them. `CONTEXT.md` records the current focus. `BRAIN.md` states how
every agent must operate in this repository.

An agent that reads those files is grounded in the specific business. An agent working
from a bare prompt is guessing. Durable, versioned, human-editable files beat re-explaining
the business every session, and they let the work accumulate instead of resetting.

## Local-first and git-friendly

The brain is plain files on disk. It lives in a normal git repository, so business truth
is diffable, reviewable, and reversible. Living business files keep stable paths and are
edited in place; execution work lands in dated folders. Credentials, customer exports,
and machine-local state stay out of git by design.

Generated runtime skill copies and local runtime state are never committed. They are
derived artifacts, checked by content hash and regenerated on demand, so the tracked
repository stays clean and the working copy stays current.

## Runtime-neutral

Claude Code and Codex are wired from the same packaged skills. There is one skill source
inside the engine, and each runtime gets a generated copy in its own directory. `/mos-onboard`
in Claude Code and `$mos-onboard` in Codex load identical workflows.

The brain does not belong to a runtime. Any agent that can read files and run a CLI can
operate it. Supporting a new runtime means adding a target directory for the generated
copies, not rewriting the system.

Nor does the brain need a runtime at all. The local app drives the CLI directly, so someone
with neither Claude Code nor Codex installed can still create a brain, fill it in, and read
what it says. The one part that does want a runtime is the assisted interview, which is
`mos assist ask` underneath: without one, the app asks the questions and takes the answers,
just without help drafting them.

## Why this holds

Each principle protects the others. A CLI that reports rather than guesses is only
trustworthy because the one place it may ask a model is named, bounded, and writes nothing.
Grounding only works because the files are the durable source and the CLI keeps them
structurally honest. Runtime-neutrality only works because the skills are generated,
not hand-maintained per runtime. The result is a system where facts are checkable, judgment
is the agent's job, and the business brain outlives any single session.
