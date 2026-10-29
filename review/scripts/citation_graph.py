"""Citation graph among the reviewed papers.

Reads citations/bibliographies.jsonl (from fetch_bibliographies.py) and
matches each bibliography entry against the 228 reviewed papers by arXiv
identifier or by exact title (ignoring case, spacing and punctuation). As
context it also counts citations from the reviewed papers to the rest of the
six-month arXiv corpus. Writes citations/graph.json with nodes, edges and a
summary.
"""

import collections
import os
import json
import re
import statistics
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
# Working directory of the review run (reviews, records and intermediate files);
# set REVIEW_WORK to point elsewhere. Its contents are not published.
HERE = Path(os.environ.get("REVIEW_WORK", REPO / "review" / "work")).resolve()
CORPUS = REPO / "corpus" / "arxiv.json"
ARXIV_ID = re.compile(r"(?<![\d.])(\d{4}\.\d{5})(?:v\d+)?(?![\d])")


def squash(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def main():
    recs = {r["id"]: r for r in json.loads((HERE / "v2_records.json").read_text())}
    corpus = {r["arxiv_id"]: r for r in json.loads(CORPUS.read_text())}
    authors = {pid: {a.split()[-1].lower() for a in corpus.get(pid, {}).get("authors", []) if a.split()}
               for pid in corpus}
    titles = {pid: squash(r["title"]) for pid, r in corpus.items()}
    titles = {pid: t for pid, t in titles.items() if len(t) >= 30}
    bibs = {}
    for line in (HERE / "citations" / "bibliographies.jsonl").read_text().splitlines():
        b = json.loads(line)
        bibs[b["id"]] = b

    edges, corpus_cites = [], collections.Counter()
    for src, b in bibs.items():
        found = {}
        for item in b["items"]:
            sq = squash(item)
            for m in ARXIV_ID.finditer(item):
                if m.group(1) in corpus and m.group(1) != src:
                    found.setdefault(m.group(1), "arxiv-id")
            for pid, t in titles.items():
                if pid != src and pid not in found and t in sq:
                    found[pid] = "title"
        for dst, how in found.items():
            if dst in recs:
                shared = sorted(authors.get(src, set()) & authors.get(dst, set()))
                edges.append({"source": src, "target": dst, "match": how,
                              "shared_author_surnames": shared,
                              "days": (date.fromisoformat(recs[src]["date"]) - date.fromisoformat(recs[dst]["date"])).days})
            corpus_cites[src] += 1

    indeg = collections.Counter(e["target"] for e in edges)
    outdeg = collections.Counter(e["source"] for e in edges)
    nodes = [{"id": pid, "title": r["title"], "date": r["date"], "use": r["use"], "kind": r["kind"],
              "scope_group": r["scope_group"], "claims": r["claims_match_evidence"],
              "in": indeg[pid], "out": outdeg[pid], "bib_size": bibs.get(pid, {}).get("n_items"),
              "bib_source": bibs.get(pid, {}).get("source"), "corpus_cites": corpus_cites[pid]}
             for pid, r in recs.items()]

    # Weakly connected components.
    adj = collections.defaultdict(set)
    for e in edges:
        adj[e["source"]].add(e["target"])
        adj[e["target"]].add(e["source"])
    seen, comps = set(), []
    for pid in recs:
        if pid in seen or pid not in adj:
            continue
        stack, comp = [pid], set()
        while stack:
            x = stack.pop()
            if x in comp:
                continue
            comp.add(x)
            stack.extend(adj[x] - comp)
        seen |= comp
        comps.append(len(comp))

    fetched = [b for b in bibs.values() if b["source"] != "none"]
    summary = {
        "papers": len(recs), "bibliographies_fetched": len(fetched),
        "by_source": dict(collections.Counter(b["source"] for b in bibs.values())),
        "edges": len(edges), "by_match": dict(collections.Counter(e["match"] for e in edges)),
        "papers_citing_any": sum(1 for n in nodes if n["out"]),
        "papers_cited_by_any": sum(1 for n in nodes if n["in"]),
        "isolated": sum(1 for n in nodes if not n["in"] and not n["out"]),
        "components": sorted(comps, reverse=True),
        "edges_with_shared_author_surname": sum(1 for e in edges if e["shared_author_surnames"]),
        "median_days_between": statistics.median(e["days"] for e in edges) if edges else None,
        "edges_citing_later_paper": sum(1 for e in edges if e["days"] < 0),
        "median_bib_size_html": statistics.median(b["n_items"] for b in bibs.values() if b["source"] == "html"),
        "reviewed_papers_citing_any_corpus_paper": sum(1 for v in corpus_cites.values() if v),
        "corpus_citations_total": sum(corpus_cites.values()),
        "most_cited": [{"id": pid, "in": k, "title": recs[pid]["title"]} for pid, k in indeg.most_common(15)],
    }
    (HERE / "citations" / "graph.json").write_text(
        json.dumps({"summary": summary, "nodes": nodes, "edges": edges}, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(summary, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
