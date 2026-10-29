"""Build the static site in _site/ from the public data and figures.

    pixi run site        (runs figures/make_figures.py first)

index.html is the dataset dashboard (static/, reading data/records.json from records.py);
methods.html reports aggregates only. Every number is read from the files in review/data/,
classification/ and corpus/. No referee score, issue or verdict is published per paper.
"""

import html
import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "site"))
import records  # noqa: E402
OUT = REPO / "_site"
FIG = REPO / "_build" / "figures"


def load(path):
    return json.loads((REPO / path).read_text())


def pct(x, digits=0):
    return f"{100 * x:.{digits}f}%"


def table(header, rows):
    head = "".join(f"<th>{html.escape(h)}</th>" for h in header)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def figure(name, caption):
    svg = (FIG / f"{name}.svg").read_text()
    svg = svg[svg.index("<svg"):]
    return (f'<figure>{svg}<figcaption>{caption} '
            f'<a href="figures/{name}.pdf">PDF</a></figcaption></figure>')


def main():
    agg = load("review/data/aggregates.json")
    nums = load("_build/figures/numbers.json")
    subj = load("classification/subjects/summary.json")
    agree = load("classification/recheck/agreement.json")
    rev = agg["review"]["overall"]
    lag = agg["model_lag"]
    cit = agg["citations"]
    tr = agg["test_retest"]
    ctl = agg["control"]["groups"]
    issue_rows = [[html.escape(c["name"]), pct(c["paper_share"]), pct(c["paper_share_apr_jun"]),
                   pct(c["paper_share_jul_oct"])] for c in agg["issue_taxonomy"]["categories"] if c["id"] != "other"]
    kappa = agg["issue_taxonomy"]["agreement"]["primary_kappa_and_raw"][0]
    kappa_x = agg["issue_taxonomy"]["cross_family_agreement"]["sol_main_vs_opus"]["primary_kappa_and_raw"][0]
    axes = agree["in_frame_only"]

    body = f"""
<header>
<h1>Papers to end all papers</h1>
<p class="lede">What six months of arXiv preprints on large language models and AI agents in condensed matter,
materials and quantum research look like, measured with AI referees.
Companion data to a commentary in the Journal Club for Condensed Matter Physics.</p>
</header>

<section class="tiles">
<div><b>{nums['momentum']['papers_per_day']:.1f}</b><span>papers per day,
18 April–18 October 2026</span></div>
<div><b>{lag['lag_days_any_role']['median']} days</b><span>median age of the newest model a paper ran</span></div>
<div><b>{pct(rev['share_with_major_issue'])}</b><span>of the papers have at least one major issue</span></div>
<div><b>{pct(subj['question_supergroup_shares']['physical-world']['share'])}</b><span>of papers ask a question
about the physical world rather than about the AI</span></div>
</section>

<h2>Pace</h2>
{figure("fig-pace", "(a) Papers per month: keyword matches in an earlier 2022–2026 search (not filtered), "
        "an exponential fit, and the 228 papers studied, in the six-month window (shaded). (b) Within the window, each point is a paper: the age Δt of the newest general-purpose model it "
        "runs at submission. Triangles: more than six months. Dotted: median. Black: age of the newest flagship "
        "of the four US labs.")}

<h2>What the papers are about</h2>
<p>All {subj['n']} papers were coded from title and abstract by a GPT-6.1 Sol and a Claude Opus 5.5
coder working independently (κ = {subj['agreement']['field']['kappa']:.2f} for the field, the research
community whose expertise is needed to judge the physics, and {subj['agreement']['question']['kappa']:.2f} for the
question). A paper restricted to one class of materials belongs to that class, otherwise to the community of
the technique it concerns.
Abstracts understate physical content: papers whose AI use appears only in the body are not found
by the searches at all.</p>
{figure("fig-subjects", "(a) Field, grouped into quantum computing and information, classes of materials, "
        "techniques that apply to any material, and other fields; (b) main question. Orange: questions about the physical "
        "world. Bars are the mean of the two coders, lines are bootstrap 95% intervals over papers.")}

<h2>Model obsolescence</h2>
<p>Median lag from the release of the newest model a paper ran to its first arXiv version:
{lag['lag_days_any_role']['median']} days (IQR {lag['lag_days_any_role']['q1']:.0f}–{lag['lag_days_any_role']['q3']:.0f};
n = {lag['lag_days_any_role']['n']}), with a median of {lag['flagship_releases_since']['median']} flagship
releases in between. {pct(lag['share_using_current_frontier'])} used the current flagship;
{pct(lag['share_lag_over_365d'])} ran a newest model more than a year old.</p>
<p>See panel (b) of the pace figure.</p>

<h2>What goes wrong</h2>
<p>One GPT-6.1 Sol referee per paper read the full text of the {rev['n']} papers. The {agg['issue_taxonomy']['n_issues']}
major issues they raised were coded into a taxonomy (κ = {kappa} between Sol coders, {kappa_x} against Claude Opus).
Shares are lower bounds: referees reported the most consequential issues within 400 words.</p>
{figure("fig-issues", "Share of papers with at least one major issue of each type; dots split the window.")}
{table(["Major issue", "Papers", "Apr–Jun", "Jul–Oct"], issue_rows)}

<h2>Getting better, disclosing more</h2>
{figure("fig-trend", "Mean claims-match-evidence score (circles, left axis) and share with an AI-use statement "
        "(squares, right axis) by month. "
        "Error bars: standard error.")}

<h2>Does anyone read them?</h2>
<p>Of the {cit['late_papers']} papers submitted from 18 August, each preceded by about
{cit['mean_earlier_papers_available']:.0f} papers in the set, {cit['late_papers_citing_any_earlier_in_set']}
cite any of them, excluding probable self-citations. Of {cit['window_references']['references']:,} references in
HTML and source bibliographies, {cit['window_references']['to_window_preprints']}
({pct(cit['window_references']['share'], 1)}) point to an arXiv preprint from the window.</p>

<h2>How reliable are the measurements?</h2>
{table(["Check", "Result"], [
    ["Same 20 papers, fresh referee", f"scores identical for {tr['reproducibility']['exact']}–{tr['claims_match_evidence']['exact']} of 20, all within one point"],
    ["Shuffled re-review of 20 early and late papers", "the early–late gap persists (claims score 0.6 → 0.5 points); "
     "the gap in major-issue counts shrinks (−0.7 → −0.2)"],
    ["Abstract labels, Haiku against a blind Sol recode", f"κ = {axes['use']['kappa']} (use), {axes['scope']['kappa']} (scope), {axes['autonomy']['kappa']} (autonomy)"],
    ["Issue taxonomy, Sol against Opus", f"κ = {kappa_x}"],
    ["Control: 50 random cond-mat and quant-ph papers from the window, same prompt and model",
     f"at least one major issue in {pct(ctl['control']['share_with_major_issue']['value'])} of control papers and "
     f"{pct(ctl['ai_physics_original']['share_with_major_issue']['value'])} of the AI papers in the same categories; "
     f"substantial or severe overclaiming {pct(ctl['control']['share_substantial_or_severe_overclaiming']['value'])} "
     f"against {pct(ctl['ai_physics_original']['share_substantial_or_severe_overclaiming']['value'])}"],
    ["Same 20 AI papers re-reviewed with the control batch",
     f"major-issue share {pct(ctl['ai_rereview_original']['share_with_major_issue']['value'])} → "
     f"{pct(ctl['ai_rereview_new']['share_with_major_issue']['value'])}; overclaiming "
     f"{pct(ctl['ai_rereview_original']['share_substantial_or_severe_overclaiming']['value'])} → "
     f"{pct(ctl['ai_rereview_new']['share_substantial_or_severe_overclaiming']['value'])}"],
])}
<p>All judgements come from language models with fixed prompts (in this repository). Per-paper scores and
issues are not published; the review texts are committed to by SHA-256
(<a href="data/commitments.sha256">list</a>, <a href="data/commitments.json">bundles</a>).</p>

<h2>Data</h2>
<ul>
<li><a href="https://github.com/akhmerov/papers-to-end-all-papers/blob/main/METHODS.md">METHODS.md</a>: the full description of the data and methods behind the commentary.</li>
<li><a href="data/aggregates.json">aggregates.json</a>: all aggregate results.</li>
<li><a href="data/papers.json">papers.json</a>: factual fields of the {rev['n']} papers (models, harness,
code links, dates, AI-use statement, citation links, field and question codes).</li>
<li><a href="index.html">Dataset</a>: every paper with its labels, searchable;
<a href="data/records.json">records.json</a>.</li>
<li>Code, prompts and the query register: see the repository README.</li>
</ul>
"""
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "figures").mkdir(parents=True)
    (OUT / "data").mkdir()
    for p in FIG.glob("*.pdf"):
        shutil.copy(p, OUT / "figures" / p.name)
    for name in ("aggregates.json", "papers.json", "commitments.sha256", "commitments.json"):
        shutil.copy(REPO / "review" / "data" / name, OUT / "data" / name)
    for p in (REPO / "site" / "static").iterdir():
        shutil.copy(p, OUT / p.name)
    (OUT / "data" / "records.json").write_text(json.dumps(
        {"records": records.records(), "codebooks": records.codebooks()}, ensure_ascii=False, separators=(",", ":")))
    (OUT / "methods.html").write_text(f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Papers to end all papers: methods and findings</title><link rel="stylesheet" href="style.css"></head>
<body><nav class="top"><span class="brand">Papers to end all papers</span><a href="index.html">Dataset</a>
<a href="methods.html" aria-current="page">Methods and findings</a>
<a href="https://github.com/akhmerov/papers-to-end-all-papers">Repository</a></nav>
<main class="narrow">{body}</main></body></html>
""")
    (OUT / ".nojekyll").write_text("")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
