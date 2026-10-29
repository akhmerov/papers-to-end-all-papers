# Full-text review

All 228 arXiv papers in the window with a substantive or proposed language-model
role (from the [classification](../classification/)) were read in full by one
GPT-6.1 Sol referee each, using [prompts/review-v2.txt](prompts/review-v2.txt).
A pilot of 20 papers used [prompts/review-v1.txt](prompts/review-v1.txt).
Each referee wrote a short report and a structured record: scores, overclaiming
level, major issues, and facts such as the models used, harness, code links and
whether an AI-use statement exists.

## What is published and what is not

Publishing per-paper scores and issues would amount to calling out individual
authors on the strength of a language model's reading, so only aggregates of
judgements are published. Facts that anyone can read off a paper are
published per paper.

| Published | Not published |
| --- | --- |
| [data/papers.json](data/papers.json): per-paper facts (models and roles, harness, code links, evaluation dates as stated, AI-use statement, model lag, citation links, subject codes) | Referee reports and per-paper scores, overclaiming levels, issues and verdicts |
| [data/aggregates.json](data/aggregates.json): all aggregate results; summaries of groups with fewer than 10 papers are suppressed | Per-issue taxonomy coding and the verified examples |
| [data/model_lag.json](data/model_lag.json), [data/citations.json](data/citations.json), [data/model-dates/](data/model-dates/) (release dates with sources) | |
| [data/commitments.sha256](data/commitments.sha256), [data/commitments.json](data/commitments.json) | |

The commitments fix the unpublished files: `commitments.sha256` lists the
SHA-256 of every referee report (in `sha256sum` format), and `commitments.json`
gives one hash per bundle of other files (per-paper records, issue coding,
verified examples), computed over the bundle's own `sha256sum` manifest so
that the file names, which would identify papers, stay private. Anyone given
the files later can check them with `sha256sum -c`.

[../tools/export_public.py](../tools/export_public.py) is the only step that
reads the unpublished files; it writes everything in [data/](data/), and
[../tools/check_public.py](../tools/check_public.py) fails if a per-paper
judgement or a local path appears in the published data.

## Pipeline

The scripts in [scripts/](scripts/) operate on a working directory given by
`REVIEW_WORK` (default `review/work/`, not tracked), which holds the referee
reports and intermediate records:

| Step | Script or prompt |
| --- | --- |
| Pilot sample and full frame | `sample.py`, `full_frame.py` |
| Referee runs | [prompts/review-v2.txt](prompts/review-v2.txt) through [../agents/run_agents.py](../agents/run_agents.py); progress with `review_queue.py` |
| Parse and summarise | `analyze_v2.py` → `v2_records.json`, `v2_summary.json` |
| Reviewer drift check | `drift_check.py` (20 papers re-reviewed in one shuffled batch) |
| Model release dates | [prompts/model-dates.txt](prompts/model-dates.txt) (three agents) → [data/model-dates/](data/model-dates/) |
| Model lag | `model_names.py`, `model_lag.py` |
| Trends | `trend_checks.py` (Spearman with average ranks for ties, permutation p) |
| Citations | `fetch_bibliographies.py`, `citation_graph.py` |
| Issue taxonomy | [prompts/issue-taxonomy.txt](prompts/issue-taxonomy.txt), [prompts/issue-coding.txt](prompts/issue-coding.txt), `taxonomy_summary.py` |
| Control sample | [control/sample.py](control/sample.py) → [control/sample.json](control/sample.json); the same review prompt on 50 control papers and 20 re-reviews in one shuffled batch; `control_compare.py` |
| Examples | [prompts/example-verification.txt](prompts/example-verification.txt) (independent Claude Opus check of selected issues) |

## Results

### Reliability

- **Test–retest**: the same 20 papers with fresh referees gave identical scores
  for 16–19 of 20 and all within one point; overclaiming category agreed on 17.
- **Reviewer drift**: reviews ran roughly in arXiv-ID order, so paper date and
  review time are confounded. Re-reviewing 10 April–May and 10
  September–October papers in one shuffled batch left the early–late gap
  unchanged (claims match evidence 2.7→2.8 early, 3.3→3.3 late).
- **Prompt dependence**: on the 20 pilot papers, prompt v1 rated 30% and 25%
  (two runs) as substantially overclaiming and prompt v2 55%. The overclaiming
  shares are therefore prompt-relative and are not used in the commentary.
- **Issue taxonomy**: 454 major issues from 200 papers in 12 categories;
  κ = 0.94 between Sol coders and 0.89 between Sol and Claude Opus on 100
  recoded issues.

### Control sample (n = 50)

To calibrate the referee, [control/sample.py](control/sample.py) draws 50 random
arXiv preprints from the window with a `cond-mat` or `quant-ph` primary
category, in the proportions of the 130 reviewed papers with these primary
categories, and rejects papers whose title or abstract contains a search term
([control/sample.json](control/sample.json) lists every draw). The size was
fixed before any review. The unchanged review prompt and model reviewed them in
one shuffled batch with new reviews of 20 of the 130 papers;
`control_compare.py` compares the groups (`control` in
[data/aggregates.json](data/aggregates.json), 95% bootstrap intervals).

| | Control (50) | AI papers, same categories (130) | Same 20 AI papers, original → new |
| --- | --- | --- | --- |
| At least one major issue | 76% [64–88] | 84% [78–90] | 90% → 90% |
| Major issues per paper | 1.3 | 2.0 | 2.3 → 2.0 |
| Claims match evidence | 3.26 | 3.17 | 2.95 → 3.00 |
| Writing quality | 3.64 | 3.76 | 3.70 → 3.65 |
| Reproducibility | 2.86 | 2.55 | 2.10 → 2.10 |
| Substantial or severe overclaiming | 22% [12–34] | 38% [29–46] | 60% → 40% |

The referee finds major issues in most ordinary papers too. Overclaiming is
the least stable judgement between runs. The control papers claim new physical
results far more often (72% against 39%) and link code far less (24% against
65%), which reflects the kind of paper as much as anything else.

### Main aggregates (n = 228)

| Measure | Value |
| --- | --- |
| Reproducibility (1–5) | median 2, mean 2.5 |
| Writing quality | median 4, mean 3.7 |
| Claims match evidence | median 3, mean 3.2 |
| At least one major issue | 88% |
| Dated model snapshot for the system | 7% |
| Evaluation dates stated | 4% |
| Code link given | 66% |
| New result, independently validated | 17% |

Human-directed reasoning and proof papers (n = 34) against the rest
(n = 194): reproducibility 3.5 vs 2.4, claims match evidence 4.0 vs 3.0, major
issue 47% vs 95%.

### Time trend

Later papers score better: Spearman ρ with submission date is +0.37 for claims
match evidence and −0.39 for the overclaiming level (p < 0.001). The trend
holds without proof papers (+0.31) and among papers without an AI-use
statement (+0.33). AI-use statements rise from 21% of papers in the first half
of the window to 46% in the second.

### Model-to-paper lag (n = 189)

The newest general-purpose model a paper ran was released a median of 96 days
before its first arXiv version (IQR 47–213), with a median of 6 flagship
releases in between; 4% used the current flagship and 17% a newest model more
than a year old. The lag does not change over the window (ρ = 0.01). Release
dates are lower bounds on evaluation dates.

### Citations

Of the 84 papers submitted from 18 August, each preceded by about 185 papers in
the set, 24 cite any of them, excluding probable self-citations. Of 9,992
references in HTML and source bibliographies, 285 (2.9%) point to an arXiv
preprint from the window. Counts are lower bounds.

All values are in [data/aggregates.json](data/aggregates.json).
