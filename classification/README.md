# Classifying the papers

Claude Haiku 5.5 labelled each of the 326 preprints of the
[reading queue](../corpus/reading-queue.csv) from its title and abstract. Labels
do not assess scientific correctness, the full text, or whether a reported
result survives independent validation. The **228 preprints with a substantive
or proposed role of a language model** are the papers of the study: they were
reviewed in full ([../review/](../review/)) and coded for field and question
([subjects/](subjects/)). The role is substantive when a language model does
scientific work, processes scientific data or evaluates research, and proposed
when such a role is proposed but not demonstrated; writing assistance,
background comparisons and passing mentions do not count.

The labels and supporting excerpts are in [classified.csv](classified.csv) and
[classified.json](classified.json); the dataset page of the project site shows
those of the 228 papers.

## Axes

| Axis | What it records |
| --- | --- |
| Scientific scope | Condensed matter; materials science; adjacent quantum research; other physics; molecular chemistry; cross-domain science; general methods; out of scope; unclear |
| Primary scientific use | Reasoning/proof; simulation execution; experimental control; data interpretation; design/optimization; property prediction; literature/knowledge; scientific QA; code/algorithm generation; research orchestration; agent evaluation; no substantive application; unclear |
| Agent form | Tool-using agent; interacting multi-agent system; fixed LLM pipeline; single model; human–AI collaboration; no LLM application; unspecified |
| Autonomy | Single step; human in loop; bounded multistep; explicit feedback loop; not applicable; unspecified |
| Task breadth | Single task; connected workflow; reusable platform; field overview; unclear |
| Paper kind | Application; method; benchmark; review/perspective; proposal; other |
| LLM role | Substantive; proposed; incidental; absent; unclear |

[taxonomy.json](taxonomy.json) defines the labels precisely. Scientific domain
and task breadth are separate meanings of scope. Multiple scientific uses can
coexist; one is primary and up to three are secondary. A model ensemble is not
automatically a multi-agent system, and an author saying “agent” does not
establish tool use or autonomous execution. Non-agentic scientific LLM uses are
kept visible rather than relabeled as agents.

Primary scientific scope is exclusive. An explicit lead review can add
`application_scopes` to a mixed-domain paper whose abstract demonstrates a
condensed-matter or materials application. This avoids losing relevant
cross-domain frameworks. These additional tags are not exhaustive for all
papers; unreviewed mixed scopes remain provisional. Main-scope reading groups
include these explicit additional scopes. Scope-table columns may therefore
overlap even though primary-scope counts do not.

## Evidence and review

The initial pass uses Claude Haiku 5.5 with tools and worker notification hooks
disabled. The exact prompt is [instructions.txt](instructions.txt), the output
schema is [schema.json](schema.json), and batch provenance is in
the batch receipts (not published). Each record retains its initial model
labels even when a reviewer changes the displayed labels. Confidence describes
the classification evidence, not the quality or correctness of the science.

Every label has a short source excerpt and a rationale. The export checks the
excerpt against the supplied text. An exact or normalized substring match
establishes that the excerpt exists; it does not prove the interpretation.
Missing abstracts, unclear roles, inconsistent labels and unmatched excerpts
are flagged for further review rather than silently accepted as applications.

An independent Opus pilot audit and selected further audits check architecture,
autonomy, mixed scientific scopes, and proposal-versus-demonstration claims.
The pilot findings are in [pilot-review.json](pilot-review.json). Accepted
changes and explicit lead checks are recorded in [lead-review.json](lead-review.json).
Selected additional audit coverage and findings are in
[selected-audits.json](selected-audits.json).
This is an assisted classification, not an independent full-text assessment of
every record. The review coverage and unresolved flags accompany the exports.

## Reproduction

```sh
python3 classification/classify.py prepare
python3 classification/classify.py run --workers 3
python3 classification/classify.py report
```

The classification ran on a queue that also contained journal records from
OpenAlex; the published files keep its arXiv records.

The runner uses the installed authenticated Claude CLI. Successful batches are
reused; worker prompts and full raw responses are in ignored `work/`. Failed
batches retain failure receipts and are retried explicitly by rerunning their
IDs with `--only`. No credential values are accessed by this script.
If an otherwise valid response omits records, `repair.py` requests only the
missing IDs, validates their exact membership, and preserves both the failed
receipt and repair hashes rather than accepting a partial classification.
The portable outputs preserve labels, evidence, prompt/schema, batch hashes,
model usage, review overrides, and validation. `validation.json` checks complete
membership, enums, evidence matching, source-queue identity and output hashes.

Scientific claims, the exact evaluated model/harness, evaluation dates and
independent verification still require full-text review. Acknowledgments,
writing-assistance declarations and reference lists are not substantive-use
evidence for that later review.

In this repository, `classify.py` and this README were adapted to the new
layout, so their hashes in `validation.json` record the published state.
