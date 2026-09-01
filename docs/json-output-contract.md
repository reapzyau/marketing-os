# JSON Output Contract

Every `mos` command returns the same envelope. Pass `--json` to any command to get
it verbatim, printed with `indent=2` and `sort_keys=True`. The envelope is
constructed in `src/marketing_os/core/results.py` and its shape is pinned by the
contract tests in `tests/contracts/`. Human output is a rendering of this
structure and carries no information the envelope lacks.

## Envelope

Every envelope carries these seven keys:

| Field | Type | Meaning |
|-------|------|---------|
| `schema` | string | `mos.<command>.v1` — the contract identity and version. |
| `command` | string | The command that produced the result. |
| `ok` | boolean | Whether the command succeeded. Drives the process exit code. |
| `repo` | string | The absolute, resolved repository path. |
| `changes` | array of string | Human-readable descriptions of planned or applied changes. Empty for read-only commands. |
| `findings` | array of finding | Problems detected (see below). Empty when nothing is wrong. |
| `next_action` | object | The single recommended next step (see below). |

The contract tests assert that these keys are always present:

```python
REQUIRED_KEYS = {"schema", "command", "ok", "repo", "changes", "findings", "next_action"}
```

Beyond the required seven, each command adds its own factual keys (for example
`repo_state`, `context`, `runtimes`, and `installed_skills` on `status`; `checks`
on `doctor`; `summary` on `validate`; `applied`, `planned`, and `runtime` on the
mutating commands). `onboard` adds two mode facts on success:

- `mode` — the chosen repository mode (`in-house`, `agency`, or `client`). It also
  appears on `status`, `doctor`, and `statusline`, where it is `null` for a legacy
  repo whose config predates modes.
- `suggested_repo_name` — the advisory folder name: `{slug}-hq` for in-house/agency,
  `{agency-slug}-{slug}` for client.

Consumers should read known keys and ignore the rest.

## `schema`

The `schema` value is `mos.<command>.v1`, where `<command>` is the command name.
Observed values include `mos.setup.v1`, `mos.status.v1`, `mos.validate.v1`,
`mos.doctor.v1`, `mos.install.v1`, and `mos.skills-sync.v1`. The `v1` suffix is the
stability promise: the seven required keys and their meanings will not change
within `v1`. New optional facts may be added; existing ones will not be removed or
repurposed under the same version. One documented exception exists, in the context
field entry below: `complete`, `ready` and `missing` widened from "answered at the
canonical path" to "answered anywhere in the brain" when discovery landed, and the
narrower reading is preserved under the new `source` key.

## Finding

Each entry in `findings` describes one problem:

| Field | Type | Meaning |
|-------|------|---------|
| `code` | string | A stable machine identifier (e.g. `missing-directory`, `skill-conflict`, `not-marketing-os`). |
| `severity` | string | `error` (default) or `warning`. |
| `message` | string | A human-readable explanation. |
| `path` | string | The offending path, or `""` when not path-specific. |

`ok` and the exit code are governed by `error` findings only. A result can carry
`warning` findings (for example, `unknown-top-level`) and still be `ok`.

## Next action

`next_action` names exactly one recommended step:

| Field | Type | Meaning |
|-------|------|---------|
| `id` | string | A stable action identifier (e.g. `run-setup`, `sync-skills`, `apply-skill-sync`). |
| `reason` | string | A short, human-readable justification. |

When nothing is required, it defaults to
`{"id": "none", "reason": "No further action is required."}`.

## Context field

`status` and `doctor` carry a `context` object whose `fields` map holds one record per
context field. `mos context show` reports the same facts, one per entry in its own
`fields` array.

| Field | Type | Meaning |
|-------|------|---------|
| `path` | string | The canonical path the schema names for this field. It does not move: it is where `mos context set` writes and what `mos validate` measures, whether or not the answer currently lives there. For `offer` it is the shape `business/offers/<offer-slug>/offer.md`, not a file expected to exist. |
| `complete` | boolean | Whether the field is answered at all — at `path`, or in the file `discovered_path` names. |
| `source` | string | Which of those it is: `canonical` (the file at `path` holds the answer), `discovered` (another file in the brain does), or `missing` (nothing does). Present on every field entry. |
| `discovered_path` | string | The repo-relative file that answered. Present only when `source` is `discovered`. |
| `files` | array of string | `offer` only: every offer document the brain holds. |
| `truncated` | boolean | Present, and always `true`, only when the search hit its budget before finishing. A `missing` verdict beside it means "not found in what was looked at", not "not there". |

`context` is measured for whatever folder is pointed at, including one that is not a brain:
a directory with no `.mos/config.yaml` still reports the fields it already answers, which is
what lets onboarding stop asking for what is already written down. `repo_state` remains the
only gate on whether the folder is a brain, so `context.ready` can be `true` beside
`repo_state: "absent"` — the answers are there and the brain is not built yet. Read the two
together; neither one answers the other's question.

Read the answer from `discovered_path` when it is present and from `path` otherwise. `mos
context show` already does that for you: its `body` carries the words that made `complete`
true wherever those words live, and `answered_in` names the file they came from.

**Compatibility.** `complete` is the one pre-existing key whose meaning widened when
discovery landed: it used to mean "the file at `path` holds real content" and now means
"this field is answered somewhere". `ready` and `missing` widened with it, which is the
point of the feature — a brain that answered a question in a folder of its owner's naming
is ready to work. Nothing was removed, and the older, narrower reading is recoverable
exactly, as `source == "canonical"`. That recovery is why `source` is written on every
entry rather than only on the interesting ones. The one place the envelope can mislead a
consumer that ignores it: on a discovered field, `complete` is `true` while `path` still
points at an untouched stub.

## Example

A planned `mos onboard . --name "Acme Co" --mode in-house` on a fresh path:

```json
{
  "schema": "mos.onboard.v1",
  "command": "onboard",
  "ok": true,
  "repo": "/home/user/acme",
  "changes": [
    "create BRAIN.md",
    "create .mos/config.yaml",
    "create .claude/skills/mos-onboard"
  ],
  "findings": [],
  "next_action": {
    "id": "apply-onboard",
    "reason": "Apply the reviewed onboard plan."
  },
  "applied": false,
  "planned": true,
  "mode": "in-house",
  "suggested_repo_name": "acme-co-hq"
}
```

## The `choose-mode` refusal

`--mode` is required. Running `mos onboard` without it is a documented contract
case: the command writes nothing, returns `ok: false` with a `mode-required`
finding, and points at the `choose-mode` next action whose `reason` is the
self-contained question to relay to the user.

```json
{
  "schema": "mos.onboard.v1",
  "command": "onboard",
  "ok": false,
  "repo": "/home/user/acme",
  "changes": [],
  "findings": [
    {
      "code": "mode-required",
      "severity": "error",
      "message": "Onboard requires --mode; choose in-house, agency, or client.",
      "path": ""
    }
  ],
  "next_action": {
    "id": "choose-mode",
    "reason": "Ask the user: are you marketing one brand you run in-house, or running an agency that serves clients? Choices: in-house (one brand you own), agency (you serve clients; creates the agency HQ with a client registry), client (a brain for one agency client). Then re-run onboard with --mode <choice> (client mode: add --agency <agency name>)."
  },
  "applied": false,
  "planned": false
}
```

A failing command returns the same envelope with `ok: false` and a populated
`findings` array — never a stack trace. Uncaught `OSError` and `ValueError` are
caught and reported as a single `command-error` finding.

## Stability expectations

- The seven required keys are guaranteed for every command, in every state.
- `ok` is authoritative: exit code is `0` when `ok` is true, `1` otherwise.
- `schema` identifies the contract version; treat unknown extra keys as additive.
- Finding `code` and next-action `id` values are stable identifiers meant for
  branching in downstream automation; parse them, not the human `message`/`reason`.
