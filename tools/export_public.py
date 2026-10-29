"""Write the public data of this repository from the unpublished working tree.

    python3 -I tools/export_public.py PRIVATE_DIR

PRIVATE_DIR is the working directory of the full-text review (the layout that
review/scripts/ writes: reviews-v2/, v2_records.json, model_lag.json, ...).
Its review texts and per-paper judgements stay private. This script publishes:

- review/data/papers.json: factual per-paper fields (models, harness, code
  links, dates, AI-use statement, model lag, citation links, subject codes);
- review/data/aggregates.json: aggregate results, with cells of fewer than
  MIN_CELL papers suppressed;
- review/data/model_lag.json and review/data/citations.json: per-paper facts;
- review/data/commitments.sha256 and review/data/commitments.json: SHA-256
  commitments to the unpublished files, so that they can be shown later to be
  the ones the analysis used.

No score, overclaiming level, issue or verdict is written per paper.
"""

import collections
import hashlib
import json
import math
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "review" / "data"
MIN_CELL = 10

# Per-paper fields kept from the referee's structured output: facts that can be
# read off the paper, not assessments of it.
FACT_FIELDS = ("date", "title", "scope_group", "use", "kind", "harness", "harness_class", "base_models",
               "dated_system_snapshot", "eval_dates_stated", "evaluation_dates", "code_urls", "ai_use_statement")
# Files whose contents stay private; they are committed to by hash.
PRIVATE_PER_FILE = ("reviews/*.md", "reviews-retest/*.md", "reviews-v2/*.md", "reviews-drift/*.md",
                    "reviews-control/*.md")
PRIVATE_BUNDLES = {
    "per-paper review data": ("v2_records.json", "tally.json", "tally-retest.json", "drift_check.json",
                              "to-verify.md", "code_link_status.tsv"),
    "issue taxonomy coding": ("taxonomy/issues.jsonl", "taxonomy/coded-*.json", "taxonomy/candidates.md"),
    "verified examples": ("examples/cases.json", "examples/wording.json", "examples/verify/*.json"),
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def suppress(node):
    """Replace any group summary with fewer than MIN_CELL papers by its size."""
    if isinstance(node, dict):
        if isinstance(node.get("n"), int) and node["n"] < MIN_CELL and len(node) > 1:
            return {"n": node["n"], "suppressed": f"fewer than {MIN_CELL} papers"}
        return {k: suppress(v) for k, v in node.items()}
    if isinstance(node, list):
        return [suppress(v) for v in node]
    return node


def mean_se(values):
    n = len(values)
    mu = sum(values) / n
    sd = math.sqrt(sum((x - mu) ** 2 for x in values) / (n - 1)) if n > 1 else 0.0
    return round(mu, 3), round(sd / math.sqrt(n), 3)


def test_retest(first, second):
    a = {r["arxiv_id"]: r for r in first}
    second = second["retest"] if isinstance(second, dict) and "retest" in second else second
    b = {r["arxiv_id"]: r for r in (second.values() if isinstance(second, dict) else second)}
    ids = sorted(set(a) & set(b))
    out = {"n": len(ids)}
    for k in ("reproducibility", "writing_quality", "claims_match_evidence"):
        d = [b[i][k] - a[i][k] for i in ids]
        out[k] = {"exact": sum(x == 0 for x in d), "within_1": sum(abs(x) <= 1 for x in d),
                  "mean_shift": round(sum(d) / len(d), 2)}
    out["overclaiming_same"] = sum(a[i]["overclaiming"] == b[i]["overclaiming"] for i in ids)
    return out


def subject_codes(repo):
    """Field and question codes of each paper, per coder (classification/subjects/)."""
    sub = repo / "classification" / "subjects"
    codes = {}
    for axis in ("field", "question"):
        for coder in ("sol", "opus"):
            for c in json.loads((sub / f"coded-{axis}-{coder}.json").read_text()):
                codes.setdefault(c["id"], {}).setdefault(coder, {})[axis] = c[axis]
    return codes


# First and last arXiv identifiers submitted in the window (18 April 00:00 to 18 October 23:59 UTC),
# from the arXiv API: 2604.16754 was submitted on 17 April at 23:57, 2610.25596 on 19 October at 00:02.
WINDOW_IDS = ("2604.16755", "2610.25595")


def window_references(private):
    """Share of references that point to an arXiv preprint submitted in the window."""
    total = window = 0
    pattern = re.compile(r"(?<![\d.])(26(?:0[4-9]|10)\.\d{5})(?:v\d+)?(?!\d)")
    in_window = lambda i: WINDOW_IDS[0] <= i <= WINDOW_IDS[1]
    for line in (private / "citations" / "bibliographies.jsonl").read_text().splitlines():
        rec = json.loads(line)
        if rec["source"] not in ("html", "source"):
            continue
        total += len(rec["items"])
        window += sum(any(in_window(m) for m in pattern.findall(item)) for item in rec["items"])
    return {"references": total, "to_window_preprints": window, "share": round(window / total, 4),
            "note": "HTML and source bibliographies only; PDF-extracted lists are not itemised reliably"}


def citation_reach(graph):
    nodes = {n["id"]: n for n in graph["nodes"]}
    nonself = [e for e in graph["edges"] if len(e.get("shared_author_surnames", [])) < 2]
    late = [i for i, n in nodes.items() if n["date"] >= "2026-08-18"]
    citing = {e["source"] for e in nonself}
    return {
        "late_papers": len(late),
        "late_papers_citing_any_earlier_in_set": len(citing & set(late)),
        "mean_earlier_papers_available": round(sum(sum(1 for j in nodes.values() if j["date"] < nodes[i]["date"])
                                                   for i in late) / len(late), 1),
        "non_self_citations_in_set": len(nonself),
        "references_total": sum(n.get("bib_size") or 0 for n in nodes.values()),
        "definition": "late = submitted from 18 August 2026; self-citation = at least two shared author surnames",
    }


def history_counts(candidates_path):
    """Keyword-matched candidates per half-year in the earlier 2022-2026 search (unscreened)."""
    import datetime as dt
    cand = json.loads(candidates_path.read_text())
    hits = [r["submitted"][:10] for r in cand if r["triage"] == "candidate-needs-screening"]
    end = max(hits)
    rows = []
    for year in range(2022, int(end[:4]) + 1):
        for half, (a, b) in enumerate(((f"{year}-01-01", f"{year}-06-30"), (f"{year}-07-01", f"{year}-12-31"))):
            if a > end:
                continue
            b = min(b, end)
            days = (dt.date.fromisoformat(b) - dt.date.fromisoformat(a)).days + 1
            rows.append({"period": f"{year}H{half + 1}", "start": a, "end": b, "days": days,
                         "candidates": sum(a <= x <= b for x in hits)})
    return {"definition": "arXiv records with a language-model or named-model cue and a domain cue in title or "
                          "abstract, before screening; precision is not calibrated and may change over time",
            "queries": "corpus/history/queries.json", "periods": rows}


def main(private):
    private = Path(private).resolve()
    OUT.mkdir(parents=True, exist_ok=True)
    recs = json.loads((private / "v2_records.json").read_text())
    lag = json.loads((private / "model_lag.json").read_text())
    graph = json.loads((private / "citations" / "graph.json").read_text())
    lag_by_id = {p["id"]: p for p in lag["papers"]}
    nodes = {n["id"]: n for n in graph["nodes"]}
    codes = subject_codes(REPO)

    papers = []
    for r in sorted(recs, key=lambda r: r["id"]):
        p = {"id": r["id"], **{k: r[k] for k in FACT_FIELDS}}
        p["models"] = [{"name": m[0], "version": m[1], "role": m[2]} for m in r["all_models"]]
        lp = lag_by_id.get(r["id"])
        if lp:
            p["model_lag"] = {k: lp[k] for k in ("newest_model", "newest_release", "newest_class", "lag_days",
                                                 "frontier_at_paper", "flagship_releases_since")}
        n = nodes.get(r["id"], {})
        p["citations"] = {"cites_in_set": n.get("out"), "cited_by_in_set": n.get("in"), "bibliography_size": n.get("bib_size")}
        c = codes.get("arxiv:" + r["id"])
        if c:
            p["field_and_question"] = c
        papers.append(p)
    (OUT / "papers.json").write_text(json.dumps(papers, indent=1, ensure_ascii=False) + "\n")
    (OUT / "model_lag.json").write_text(json.dumps(lag, indent=1, ensure_ascii=False) + "\n")
    public_graph = {"summary": graph["summary"],
                    "nodes": [{k: v for k, v in n.items() if k != "claims"} for n in graph["nodes"]],
                    "edges": graph["edges"]}
    (OUT / "citations.json").write_text(json.dumps(public_graph, indent=1, ensure_ascii=False) + "\n")

    summary = json.loads((private / "v2_summary.json").read_text())
    summary.get("prompt_v1_vs_v2", {}).pop("papers", None)
    drift = json.loads((private / "drift_check.json").read_text())
    monthly = collections.defaultdict(list)
    for r in recs:
        monthly[r["date"][:7]].append(r)
    by_month = {}
    for m, rs in sorted(monthly.items()):
        claims_mean, claims_se = mean_se([r["claims_match_evidence"] for r in rs])
        p = sum(bool(r["ai_use_statement"]) for r in rs) / len(rs)
        by_month[m] = {"n": len(rs), "claims_mean": claims_mean, "claims_se": claims_se,
                       "ai_use_share": round(p, 3), "ai_use_se": round(math.sqrt(p * (1 - p) / len(rs)), 3)}
    issue_summary = json.loads((private / "taxonomy" / "summary.json").read_text())
    aggregates = {
        "min_cell": MIN_CELL,
        "review": suppress(summary),
        "by_month": suppress(by_month),
        "trend": json.loads((private / "trend_checks.json").read_text()),
        "drift_check": {"n": drift["n"], "metrics": drift["metrics"]},
        "test_retest": test_retest(json.loads((private / "tally.json").read_text()),
                                   json.loads((private / "tally-retest.json").read_text())),
        "issue_taxonomy": issue_summary,
        "model_lag": lag["summary"],
        "citations": {**graph["summary"], **citation_reach(graph), "window_references": window_references(private)},
        # Control sample: ordinary cond-mat and quant-ph papers reviewed with the same prompt and model
        # (review/control/, review/scripts/control_compare.py).
        "control": suppress(json.loads((private / "control_compare.json").read_text())),
    }
    candidates = private.parents[1] / "candidates.json"
    if candidates.exists():
        hist = REPO / "corpus" / "history" / "half-year-counts.json"
        hist.write_text(json.dumps(history_counts(candidates), indent=1) + "\n")
    (OUT / "aggregates.json").write_text(json.dumps(aggregates, indent=1, ensure_ascii=False) + "\n")

    lines = []
    for pattern in PRIVATE_PER_FILE:
        for path in sorted(private.glob(pattern)):
            lines.append(f"{sha256(path)}  {path.relative_to(private)}")
    (OUT / "commitments.sha256").write_text("\n".join(lines) + "\n")
    bundles = {}
    for name, patterns in PRIVATE_BUNDLES.items():
        files = sorted({p for pat in patterns for p in private.glob(pat)})
        # The bundle hash covers each file's relative path and hash, so file names
        # (which would reveal which papers are involved) are not published.
        manifest = "".join(f"{sha256(p)}  {p.relative_to(private)}\n" for p in files)
        bundles[name] = {"files": len(files), "sha256_of_manifest": hashlib.sha256(manifest.encode()).hexdigest()}
    (OUT / "commitments.json").write_text(json.dumps({
        "per_file": "commitments.sha256 (sha256sum format, paths relative to the private working tree)",
        "bundles": bundles,
        "bundle_rule": "sha256 of the sha256sum-format manifest of the bundle's files, sorted by path",
    }, indent=1) + "\n")
    print(f"{len(papers)} papers; {len(lines)} per-file commitments; bundles "
          + ", ".join(f"{k}: {v['files']}" for k, v in bundles.items()))


if __name__ == "__main__":
    main(sys.argv[1])
