# Papers to end all papers

Data, code and prompts behind a commentary in the
[Journal Club for Condensed Matter Physics](https://www.condmatjclub.org) on how
large language models and AI agents are used in condensed matter, materials and
quantum research. It studies the 228 arXiv preprints of six months
(18 April–18 October 2026) that give a language model a substantive role: how
many appear, what they are about, how old the models they use are, how they
cite each other, and what goes wrong in them, using AI referees whose
reliability is checked along the way.

The project site, built from this repository by
[.github/workflows/pages.yml](.github/workflows/pages.yml), is a searchable
dashboard of the dataset (every paper with its labels, filters and linked
charts) with a page of methods and aggregate findings.

[METHODS.md](METHODS.md) describes the data and methods behind every number in
the commentary, including the parts that are not in the commentary itself.

## Layout

| Directory | Contents |
| --- | --- |
| [corpus/](corpus/) | Search protocol, query register, frozen arXiv snapshot, reading queue, and a dependency-free replay of the searches |
| [classification/](classification/) | Title/abstract labels of the 326 preprints of the reading queue, which select the 228 papers; the blind recheck by a second model, an LLM-free topic model, and the field and question coding of the 228 papers |
| [review/](review/) | Full-text review of the 228 papers: prompts, pipeline scripts, published per-paper facts, aggregates and hash commitments |
| [agents/](agents/) | A generic runner for the agent prompts, and which models ran which prompt |
| [figures/](figures/), [site/](site/) | Figures, and the static site: dataset dashboard ([site/static/](site/static/), data from [site/records.py](site/records.py)) and methods page |
| [tools/](tools/) | The private-to-public export and the check that guards it |

## What is not published

Per-paper scores, overclaiming levels, major issues and verdicts written by the
AI referees are not published, and neither are the referee reports: they are
model judgements about identifiable authors' work. They enter only as
aggregates: any summary of a group of papers defined by a public attribute
(kind, scope, month, ...) is suppressed when the group has fewer than 10
papers. Distributions over the whole reviewed set (for example, how many papers
received each score) are published; they do not say which papers they contain. SHA-256
commitments in [review/data/](review/data/) fix the unpublished files; see
[review/README.md](review/README.md). Facts that can be read off a paper (models
used, code links, dates, AI-use statement, citations) are published per paper.

## Reproducing

```sh
pixi run check      # no per-paper judgements, non-arXiv records or local paths
pixi run figures    # figures from the public data, into _build/figures/
pixi run site       # static site, into _site/
pixi run agreement  # coder agreement and subject shares from the published codes
pixi run rehash     # refresh classification/validation.json after editing a file it lists
pixi run lexical    # LLM-free topic model of the abstracts
pixi run replay     # re-run the registered searches (network; see corpus/README.md)
```

The figures, the site, the coder agreement, the field and question shares and
the topic model are reproducible from the published data. The agent runs
themselves can be repeated with [agents/run_agents.py](agents/run_agents.py) and any command-line coding agent,
but will not give identical labels; the reliability checks quantify by how
much. Steps that need the unpublished reports (`review/scripts/`,
`tools/export_public.py`) read them from `REVIEW_WORK`.

## Publishing the site

After pushing to GitHub, enable Pages with GitHub Actions as the source
(Settings → Pages → Build and deployment → GitHub Actions, or
`gh api -X POST repos/akhmerov/papers-to-end-all-papers/pages -f build_type=workflow`). Each push to
`main` then checks the data, draws the figures and deploys `_site/`.

## Licence

Code: BSD 2-Clause ([LICENSE](LICENSE)). Data and text: CC BY 4.0. The corpus
contains bibliographic metadata, including abstracts, as distributed by arXiv
under CC0.
