# Philosophy

marketing-os is built on one split: the CLI owns facts, the agent owns judgment.
Everything else follows from keeping that line clean.

## The CLI never calls a model

`mos` is deterministic and model-free. It reads and writes the filesystem, validates
structure against a fixed schema, and wires runtime skill copies. Given the same
repository it always returns the same answer. Because it never reasons, it can be
trusted as ground truth: an agent asks `mos status` what is real instead of guessing.

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

## Why this holds

Each principle protects the others. A model-free CLI is only trustworthy because it never
guesses. Grounding only works because the files are the durable source and the CLI keeps
them structurally honest. Runtime-neutrality only works because the skills are generated,
not hand-maintained per runtime. The result is a system where facts are checkable, judgment
is the agent's job, and the business brain outlives any single session.
