"""Fail if published data breaks the publication rules of this repository.

    pixi run check          # the repository
    python -I tools/check_public.py --site   # also the built site in _site/

The rules (README.md, "What is not published"):
- no per-paper judgement of an AI referee (scores, overclaiming, issues, verdicts), and no reference to an
  individual paper's major issue; aggregates over fewer than MIN_CELL papers are suppressed;
- every published record is an arXiv record (arXiv metadata, including abstracts, is CC0);
- no local paths; and the digests in classification/validation.json are current.
"""

import csv
import hashlib
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MIN_CELL = 10
FORBIDDEN_KEYS = {"reproducibility", "writing_quality", "claims_match_evidence", "overclaiming", "major_issues",
                  "n_major", "minor", "minor_issue_count", "one_line_verdict", "new_scientific_result",
                  "independent_validation", "human_intervention", "verdict", "claims", "issue", "issues"}
# Files with one entry per paper or record.
PER_PAPER = ["review/data/papers.json", "review/data/model_lag.json", "review/data/citations.json",
             "classification/classified.json", "classification/lead-review.json",
             "classification/recheck/coded-*.json", "classification/subjects/coded-*.json"]
SITE_PER_PAPER = ["_site/data/records.json", "_site/data/papers.json"]
TEXT_SUFFIXES = {".py", ".txt", ".md", ".json", ".jsonl", ".csv", ".tsv", ".toml", ".yml", ".html", ".js", ".css"}
# Not published: build outputs and the environment.
UNPUBLISHED = {".pixi", "_build", "__pycache__", ".git"}
LOCAL = re.compile(r"/home/[a-z]+/|/Users/[A-Za-z]+/")
# Identifier of one major issue of one paper ("2605.01234#2"): issue-level coding is not published.
ISSUE_ID = re.compile(r"\b\d{4}\.\d{4,5}#\d+\b")
ARXIV_ID = re.compile(r"(arxiv:)?\d{4}\.\d{4,5}")


def published_files(site):
    for p in sorted(REPO.rglob("*")):
        rel = p.relative_to(REPO)
        if not p.is_file() or p.suffix not in TEXT_SUFFIXES:
            continue
        if any(part in UNPUBLISHED for part in rel.parts) or (rel.parts[0] == "_site" and not site):
            continue
        yield p


def records_of(p):
    """Records of a JSON, JSONL or CSV file, each a (record id or None, record) pair."""
    if p.suffix == ".csv":
        with p.open() as f:
            return [(r.get("id") or r.get("native_id"), r) for r in csv.DictReader(f)]
    if p.suffix == ".jsonl":
        rows = [json.loads(line) for line in p.read_text().splitlines() if line.strip()]
    elif p.suffix == ".json":
        data = json.loads(p.read_text())
        if isinstance(data, dict) and isinstance(data.get("records"), list):
            data = data["records"]
        if isinstance(data, dict) and all(isinstance(v, dict) for v in data.values()):
            return list(data.items())
        rows = data if isinstance(data, list) else []
    else:
        return []
    return [(r.get("id") or r.get("native_id") or r.get("arxiv_id"), r) for r in rows if isinstance(r, dict)]


def keys(node, path=""):
    if isinstance(node, dict):
        for k, v in node.items():
            yield path + "/" + k, k, v
            yield from keys(v, path + "/" + k)
    elif isinstance(node, list):
        for v in node:
            yield from keys(v, path + "[]")








def check_aggregates(problems):
    """Every group summary over fewer than MIN_CELL papers must be suppressed."""
    def walk(node, path):
        if isinstance(node, dict):
            if isinstance(node.get("n"), int) and node["n"] < MIN_CELL and set(node) - {"n", "suppressed"}:
                problems.append(f"review/data/aggregates.json: unsuppressed group of {node['n']} papers at {path}")
            for k, v in node.items():
                walk(v, f"{path}/{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")
    walk(json.loads((REPO / "review" / "data" / "aggregates.json").read_text()), "")






def main(site=False):
    csv.field_size_limit(10**9)
    problems = []
    v = json.loads((REPO / "classification" / "validation.json").read_text())
    problems += [f"classification/{n}: digest in validation.json is stale (pixi run rehash)"
                 for n, h in v["files"].items()
                 if hashlib.sha256((REPO / "classification" / n).read_bytes()).hexdigest() != h]
    check_aggregates(problems)
    per_paper = {q for pattern in PER_PAPER + (SITE_PER_PAPER if site else []) for q in REPO.glob(pattern)}
    for q in sorted(per_paper):
        for rid, rec in records_of(q):
            bad = sorted({k for _, k, _ in keys(rec) if k in FORBIDDEN_KEYS})
            if bad:
                problems.append(f"{q.relative_to(REPO)}: per-paper referee field {bad[0]} in {rid}")
                break
    for p in published_files(site):
        rel = p.relative_to(REPO)
        if p.suffix in (".json", ".jsonl", ".csv"):
            other = [rid for rid, _ in records_of(p) if isinstance(rid, str) and not ARXIV_ID.fullmatch(rid)]
            if other and any(ARXIV_ID.fullmatch(rid or "") for rid, _ in records_of(p) if isinstance(rid, str)):
                problems.append(f"{rel}: record that is not an arXiv record: {other[0]}")
        if p.name == "check_public.py":
            continue
        text = p.read_text(errors="ignore")
        if LOCAL.search(text):
            problems.append(f"{rel}: contains a local home-directory path")
        if ISSUE_ID.search(text):
            problems.append(f"{rel}: refers to an individual paper's major issue")
        if re.search(r"openalex\.org/W\d+", text, re.I):
            problems.append(f"{rel}: contains an OpenAlex record")
    print("\n".join(problems) or "public data check passed")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main(site="--site" in sys.argv)
