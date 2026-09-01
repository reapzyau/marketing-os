# The knowledge graph: an optional add-on

The navigation layer in `mos` — the frontmatter contract, the `_index.md` hierarchy, and
`## Related` blocks — is deterministic, ships in the CLI, and needs nothing but Python. A
knowledge graph over the same corpus is a different proposition, and this document explains
why it sits outside the tool rather than inside it.

## What a graph adds, and what it does not

The corpus this design came from was measured before and after a full navigation-layer
rollout that also included model-backed graph extraction:

| Metric | Before | After |
|---|---|---|
| Nodes / edges | 1,342 / 1,303 | 3,573 / 6,192 |
| Average degree | 1.94 | 3.47 |
| Edges crossing a top-level folder | 19% | 31% |
| Orphan nodes | 14% | 9% |
| **Documents with an outgoing link** | **2%** | **64%** |

The last row is the one an agent feels, and it did not come from the graph. A deliberate
experiment settles it: a full deep re-extraction over the same corpus found roughly two and a
half times as many entities and moved connectivity by **zero**. Extraction can only record a
relationship that a document already states. Of 1,177 documents, 27 carried a wikilink and
about 1% carried a connective frontmatter key. The corpus was not under-analysed; it was
under-declared.

So the contract, the hierarchy, and the link backfill are what moved the number, and those
are exactly the parts that need no model. The graph earns its keep on a different question —
"which documents belong together that nobody thought to link?" — and that is genuinely
useful, but it is the expensive fraction that bought the smallest share of the win.

## Why it is not in the CLI

`AGENTS.md` in the engine repository is explicit: keep the CLI deterministic and model-free.
A graph pipeline breaks that on every axis. It needs an API key and a provider account. It
costs real money per rebuild. Its output is not reproducible across runs. And it drags in
operational failure modes that have nothing to do with marketing:

- On Windows Subsystem for Linux, running the extraction against a repository on the Windows
  drive blocks in the 9P client with no progress at all; the corpus has to be mirrored onto
  the Linux filesystem first.
- Default chunking that packs dozens of files into a single request returns a prose summary
  instead of structured entities. The fix is a much smaller token budget per chunk, and there
  is no signal that anything went wrong until the output is inspected.
- Extractors typically do not resolve a `[[wikilink]]` to the target document's node, so
  every `## Related` block and every generated index is invisible to the graph until those
  edges are injected separately.

None of that belongs in a tool whose promise is that it always behaves the same way.

## If you want one anyway

Run it as a separate step outside `mos`, against your brain's folder, and keep its output in
a gitignored directory. Two things make it work well:

1. **Run the navigation layer first.** `mos index build`, `mos index sync --yes`, and
   `mos related --yes` give the extractor a corpus that states its own structure. Extraction
   quality follows declaration quality, not model size.
2. **Inject wikilink edges deterministically afterwards.** The links in `## Related` blocks
   and index files are real, authored relationships. Resolving them to graph edges is free,
   needs no model, and in the corpus above it was the single change that moved average degree
   from 1.86 to 3.47.

Treat any semantic clusters it finds as a suggestion for where a human should add a real
link. A link in the document survives the next rebuild; a cluster in a generated artifact
does not.

## Research

- Corpus2Skill, "Don't Retrieve, Navigate" (arXiv 2604.14572) — compiling a corpus into a
  tree of small navigation files beat dense retrieval on WixQA (6,221 documents): Token F1
  0.460 against 0.363, and 0.389 for RAPTOR, with better context recall (0.652 against
  0.616). Navigation files stay under 2 KB; a typical answer takes two or three navigation
  turns.
- "Is Grep All You Need?" (arXiv 2605.15184) — with a competent agent harness, filesystem
  navigation plus literal search closes most of the gap to embedding retrieval. Structure,
  meaningful names, and index files matter more than better embeddings.
