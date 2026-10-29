# Corpus: six months of arXiv preprints

A search snapshot of arXiv for **18 April–18 October 2026 inclusive** (initial
submission), acquired on 19 October 2026. Scope: applications of large language
models and agents built on them to condensed matter, materials science and
quantum research.

## Search design

Nine arXiv searches cross three vocabulary families with three search scopes:

| Vocabulary | Scopes |
| --- | --- |
| Language models, model names, foundation and vision-language models | `cond-mat.*`; `quant-ph`; domain terms across all categories |
| Agentic, AI/LLM agents, multi-agent and autonomous research | Same three scopes |
| Harness, harnesses, scaffold, scaffolding | Same three scopes |

All keyword matches are restricted to **title and abstract**. The exact
vocabulary and date policy are in [protocol.json](protocol.json); the query
specifications are in [queries/arxiv.json](queries/arxiv.json), with the totals
and stopping conditions recorded at acquisition in
[queries/arxiv-ledger.csv](queries/arxiv-ledger.csv).

Consequence of the design: papers that use language models but say so only in
the body, not in the title or abstract, are not found. These are typically
papers whose subject is physics rather than the AI, so the corpus is biased
towards papers about AI.

## Files

- [arxiv.json](arxiv.json): the 2,018 distinct preprints returned by the nine
  searches, with title, abstract, authors, dates, categories and the terms
  that matched.
- [reading-queue.csv](reading-queue.csv): the 326 preprints kept by an
  automatic filter, the input of the [classification](../classification/). The
  filter requires a language-model term or model name in the title or abstract
  (a match on *foundation model* alone does not count) and a `cond-mat` or
  `quant-ph` category or a domain term in the title. Preprints matched only by
  the agent or harness vocabulary are therefore not in the queue.
- [history/](history/): the query register of an earlier, longer search
  (2022–2026) and the number of keyword-matched, unfiltered preprints per
  half-year, used for the long-run growth curve.

## Replaying the searches

The acquisition used a private harvesting tool with a local cache; nothing in
this repository depends on it. [replay.py](replay.py) re-runs the registered
queries against the arXiv API with the Python standard library only and
compares the result with the snapshot:

```sh
pixi run replay                             # all queries
pixi run replay --only cond-mat-harnesses   # one query
```

Results go to `corpus/replay/` (not tracked). Expect small differences: arXiv
adds, withdraws and re-indexes records. As a check, replaying
`cond-mat-harnesses` on 28 October 2026 returned 140 records against 139 at
acquisition, 139 of them in the snapshot. `CONTACT_EMAIL`, if set, is sent to
arXiv as a courtesy.
