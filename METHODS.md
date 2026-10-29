# Data and methods

This is the methods description of the commentary "Papers to end all papers" in the
[Journal Club for Condensed Matter Physics](https://www.condmatjclub.org). The
commentary's figures are drawn by [figures/make_figures.py](figures/make_figures.py):
Fig. 1 is `fig-pace`, Fig. 2 `fig-subjects`, Fig. 3 `fig-issues` and Fig. 4
`fig-trend`. Every number below is read from the files of this repository.

The study covers the 228 arXiv preprints submitted between 18 April and 18 October
2026 in condensed matter, materials science and quantum research that give a
language model a substantive role. Language-model agents carried out every step:
Claude Haiku 5.5 classified the abstracts, GPT-6.1 Sol read the papers in full, and
Claude Opus 5.5 provided independent second codings and checks. The author designed
the steps and checked the agents' output; [agents/README.md](agents/README.md) lists
which model ran which prompt. Because the full-text reports are model judgements
about identifiable authors' work, they are published only as aggregates over at
least ten papers, together with SHA-256 hashes that fix the unpublished per-paper
files ([review/README.md](review/README.md)).

## Corpus

The corpus contains the arXiv preprints first submitted between 18 April and
18 October 2026 whose title or abstract matches the search terms ([corpus/](corpus/)).
The study is restricted to six recent months because the models change faster than
the papers appear: in the window, the four largest US labs released a new flagship
model every 13 days, and the newest model that a paper uses is already a median of
96 days old at submission (Fig. 1b).

The terms come in three families: language models (*large language model*, *LLM*,
*foundation model*, *vision-language*, and model names such as *GPT*, *Claude*,
*Gemini*, *Qwen* or *Llama*); agents (*agentic*, *AI agent*, *multi-agent*,
*AI scientist*, *self-driving lab*); and harnesses (*harness*, *scaffold*). The full
lists are in [corpus/protocol.json](corpus/protocol.json). Each family is searched
three times: in the `cond-mat` categories, in `quant-ph`, and in all categories
together with domain terms such as *condensed matter*, *many-body*, *DFT*,
*superconduct\**, *materials*, *crystal\** or *molecular dynamics*. These nine
searches return 2 018 distinct preprints. An automatic filter then keeps the 326
whose title or abstract contains a language-model term other than *foundation
model*, and whose category or title places them in the domain.

The filter removes papers that describe only agents without naming a language model,
and because all terms match the title and abstract, the corpus also misses papers
that mention their use of AI only in the body. Such papers are likely to be about
physics rather than about AI, which biases the corpus towards the latter. For the
long-run trend in Fig. 1a, keyword matches are counted without filtering in an
earlier arXiv search covering 2022–2026
([corpus/history/](corpus/history/)); their rate dN/dt doubles every T = 8 months.

## The papers

Claude Haiku classified each of the 326 preprints from its title and abstract by the
role of the language model, the scientific scope, the use of the model and the kind
of paper ([classification/](classification/)). The role is substantive when a
language model does scientific work, processes scientific data or evaluates
research, and proposed when such a role is proposed but not demonstrated; writing
assistance, background comparisons and passing mentions do not count. The 228
preprints with a substantive or proposed role, 1.2 per day, are the papers of the
study. By Haiku's scope labels, 196 of them concern condensed matter, materials
science or adjacent quantum research, and the other 32 in chemistry, other physics,
general methods or unrelated fields.

A blind recoding by GPT-6.1 Sol confirms the role of 227 of the 228 papers, and
agrees with the original classification on the scope (κ = 0.86) and the use
(κ = 0.82). Of 21 random preprints outside the 228, Sol places 7 among them, 5 of
these outside condensed matter, materials and quantum research
([classification/recheck/](classification/recheck/)).

## What the papers are about

To determine what the papers study, GPT-6.1 Sol agents built two codebooks from the
abstracts of an earlier, broader candidate set: the field, meaning the research
community whose expertise is needed to judge the physics of a paper, and the question
the paper answers ([classification/subjects/](classification/subjects/)). The field
codebook has an additional category for papers outside condensed matter, materials
and quantum research. One Sol and one Opus agent then coded each axis for all 228
papers independently, agreeing on the field with κ = 0.90 and on the question with
κ = 0.90. A paper restricted to one class of materials belongs to that class;
otherwise it belongs to the community of the technique it concerns, such as atomistic
simulation or microscopy. Quantum computing and quantum information account for 31%
of the papers, material classes for 28%, techniques for 31% and other fields for
10%, with quantum algorithms, circuits and software the largest single field at 17%
(Fig. 2a). Whatever the field, 86% of the papers ask a question about the AI or its
workflow rather than about the physical world (Fig. 2b); two thirds of the remaining
14% are in quantum information theory and correlated quantum matter. A topic model of
the abstracts that uses no language model leads to the same conclusion: its clusters
follow what the AI does rather than the physical system it is applied to
([classification/recheck/](classification/recheck/)).

## Full-text review

GPT-6.1 Sol read each of the 228 papers in full, following the same prompt for every
paper ([review/prompts/review-v2.txt](review/prompts/review-v2.txt)). For each paper, a separate agent wrote a referee report
of at most 400 words on reproducibility, writing quality and whether the claims
match the evidence, separating major issues, which would change a main conclusion,
from minor ones. It ended the report with a structured record: scores from 1 to 5
for each of the three criteria; the major issues, most consequential first; and
facts such as the models used, the harness, code links and the presence of an AI-use
statement. The facts are published per paper
([review/data/papers.json](review/data/papers.json)); reports, scores and issues only
as aggregates.

The prompt asks for an unbiased assessment and warns against elevating minor issues,
but its criteria and output record ask for shortcomings rather than strengths, and
its overclaiming scale (none, mild, substantial, severe) has no grade for
underclaiming. The control sample below calibrates the resulting strictness.

To test the reliability of these judgements, the review of 20 papers was repeated
with new referees: the scores were identical for 16 to 19 of the 20 papers,
depending on the score, and never differed by more than one point. The reviews ran
roughly in the order of submission, so a drift of the referee over time could mimic
a time trend. Re-reviewing 10 early and 10 late papers in one shuffled batch,
however, leaves the difference between them unchanged. The referee's judgement of
overclaiming is less stable than the scores: the share of papers that overclaim
ranges between 25% and 55% of the same 20 papers across two prompt versions and a
repeat.

## Control sample

To calibrate the referee, 50 random arXiv preprints submitted in the window with a
primary category in `cond-mat` or `quant-ph` were drawn, in the same proportions as
the 130 reviewed papers with these primary categories, excluding papers whose title
or abstract contains a search term ([review/control/](review/control/)). GPT-6.1 Sol
reviewed them with the same prompt, in one shuffled batch together with new reviews
of 20 of the 130 papers. The referee reports at least one major issue in 76% of the
control papers (95% confidence interval 64–88%) and in 84% of the 130 papers
(78–90%). The scores for how well the claims match the evidence and for writing
quality do not differ detectably between the two groups, while the papers on
language models receive more major issues: 2.0 per paper against 1.3. The new
reviews of the 20 papers reproduce the share with a major issue and the scores of
the original reviews, but the share that overclaims substantially or severely falls
from 60% to 40%. With this caveat, 22% of the control papers (12–34%) overclaim
substantially or severely, against 38% of the 130 papers (29–46%) and 40% of the 20
papers reviewed in the same batch. The papers on language models claim a new
scientific result less often than the control papers (39% against 72%), but the share
whose new result the referee considers independently validated is similar: 25% of
the 130 papers (18–32%) against 30% of the control papers (18–42%).

## What goes wrong

A Sol agent grouped the 454 major issues reported for 200 of the 228 papers into
twelve categories, shown in Fig. 3 ([review/data/issue-taxonomy.json](review/data/issue-taxonomy.json)).
Two Sol coders agree on the category with κ = 0.94, and Sol and Opus with κ = 0.89,
on 100 recoded issues. The shares are lower bounds, because each report is limited
to 400 words and lists only the most consequential issues. Of the 228 papers, 88%
have at least one major issue, 51% have one because the materials needed to
reproduce their results are not accessible, and 17% report a new scientific result
that is independently validated. An independent Opus agent checked each example of
an issue quoted in the commentary against the paper
([review/prompts/example-verification.txt](review/prompts/example-verification.txt));
all of them held up.

## Trend

Later papers match their claims to the evidence better (Fig. 4, circles; Spearman ρ = 0.37
with the submission date, p < 0.001). The trend persists when excluding the 34
papers on human-directed reasoning and proofs (ρ = 0.31) and among the papers
without an AI-use statement (ρ = 0.33). The share of papers with an AI-use statement
grows from 21% in April–June to 41% in July–October (Fig. 4, squares).

## Model age

To determine how old the models in the papers are, three Sol agents looked up the
release dates of the 386 models named in the referee records, each for a third of
them, and gave a source for every date
([review/data/model-dates/](review/data/model-dates/)). For each of the 189 papers
that run a dated general-purpose language model, the release of the newest such
model is compared with the first arXiv submission (Fig. 1b). The median lag Δt
between the two is 96 days (interquartile range 47–213), during which OpenAI,
Anthropic, Google DeepMind and xAI released a median of six flagship models; in the
window itself, these four labs released a flagship every 13 days. Only 4% of the
papers use the current flagship, 17% use a newest model that is more than a year
old, and the lag does not change over the window (ρ = 0.01). Release dates are lower
bounds on when a model was evaluated, and only 4% of the papers state the evaluation
dates; 7% name a dated model snapshot.

## Citations

To estimate how much the papers build on each other, the bibliographies of the 228
papers were extracted from their HTML, source or PDF versions
([review/data/citations.json](review/data/citations.json)). Of the 84 papers
submitted from 18 August on, each preceded by about 185 papers in the set, 24 cite
at least one of them, not counting citations between papers that share two or more
author surnames. Of the 9 992 references in the HTML and source bibliographies, 240
(2.4%) point to an arXiv preprint submitted in the window. Both numbers are lower
bounds, because the matching of references to preprints misses some citations.
