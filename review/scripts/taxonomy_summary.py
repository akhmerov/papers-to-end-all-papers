"""Summarise the coded major issues.

Reads taxonomy/taxonomy.json, taxonomy/issues.jsonl, the four coded batches
and the two independent recodes. Writes taxonomy/summary.json (aggregate
shares, agreement) and taxonomy/candidates.md (cases to verify against the
papers; private, since it names papers).
"""

import collections
import os
import json
import random
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
# Working directory of the review run (reviews, records and intermediate files);
# set REVIEW_WORK to point elsewhere. Its contents are not published.
HERE = Path(os.environ.get("REVIEW_WORK", REPO / "review" / "work")).resolve()
T = HERE / "taxonomy"


def load(pattern):
    out = {}
    for path in sorted(T.glob(pattern)):
        for c in json.loads(path.read_text()):
            out[c["issue_id"]] = c
    return out


def kappa(pairs):
    n = len(pairs)
    po = sum(a == b for a, b in pairs) / n
    ca, cb = collections.Counter(a for a, _ in pairs), collections.Counter(b for _, b in pairs)
    pe = sum(ca[k] * cb[k] for k in ca) / n ** 2
    return round((po - pe) / (1 - pe), 2), round(po, 2)


def main():
    tax = json.loads((T / "taxonomy.json").read_text())
    cats = {c["id"]: c for c in tax["categories"]}
    issues = {x["issue_id"]: x for x in map(json.loads, (T / "issues.jsonl").read_text().splitlines())}
    coded, recoded = load("coded-batch-*.json"), load("coded-recode-*.json")
    missing = sorted(set(issues) - set(coded))
    bad = sorted(i for i, c in {**coded, **recoded}.items() if c["primary"] not in cats)
    recs = {r["id"]: r for r in json.loads((HERE / "v2_records.json").read_text())}
    n_papers = len(recs)

    issue_counts = collections.Counter(c["primary"] for c in coded.values())
    papers_with = collections.defaultdict(set)
    for i, c in coded.items():
        papers_with[c["primary"]].add(issues[i]["paper"])

    def paper_share(cat, sel):
        return round(len(papers_with[cat] & sel) / len(sel), 3) if sel else None

    early = {p for p, r in recs.items() if r["date"] < "2026-07-01"}
    late = set(recs) - early
    proof = {p for p, r in recs.items() if r["use"] == "reasoning-proof"}
    rows = []
    for cid, c in cats.items():
        rows.append({
            "id": cid, "name": c["name"], "supergroup": c["supergroup"],
            "issues": issue_counts[cid], "issue_share": round(issue_counts[cid] / len(coded), 3),
            "paper_share": paper_share(cid, set(recs)),
            "paper_share_apr_jun": paper_share(cid, early), "paper_share_jul_oct": paper_share(cid, late),
            "paper_share_proof": paper_share(cid, proof), "paper_share_rest": paper_share(cid, set(recs) - proof),
        })
    rows.sort(key=lambda r: -r["issues"])
    sg = collections.defaultdict(set)
    for i, c in coded.items():
        if c["primary"] in cats:
            sg[cats[c["primary"]]["supergroup"]].add(issues[i]["paper"])

    both = [i for i in recoded if i in coded]
    pairs = [(coded[i]["primary"], recoded[i]["primary"]) for i in both]
    sg_pairs = [(cats[a]["supergroup"], cats[b]["supergroup"]) for a, b in pairs if a in cats and b in cats]
    lenient = sum(coded[i]["primary"] == recoded[i]["primary"] or coded[i].get("secondary") == recoded[i]["primary"]
                  or recoded[i].get("secondary") == coded[i]["primary"] for i in both)
    confusions = collections.Counter(tuple(sorted(p)) for p in pairs if p[0] != p[1])
    opus = load("coded-opus-*.json")
    cross = {}
    for name, other in (("sol_main_vs_opus", coded), ("sol_recode_vs_opus", recoded)):
        ids = [i for i in opus if i in other]
        pr = [(other[i]["primary"], opus[i]["primary"]) for i in ids]
        sgp = [(cats[a]["supergroup"], cats[b]["supergroup"]) for a, b in pr if a in cats and b in cats]
        loose = sum(other[i]["primary"] == opus[i]["primary"] or other[i].get("secondary") == opus[i]["primary"]
                    or opus[i].get("secondary") == other[i]["primary"] for i in ids)
        cross[name] = {"n": len(ids), "primary_kappa_and_raw": kappa(pr) if pr else None,
                       "supergroup_kappa_and_raw": kappa(sgp) if sgp else None,
                       "primary_or_secondary_match": round(loose / len(ids), 2) if ids else None,
                       "top_confusions": [[a, b, n] for (a, b), n in collections.Counter(
                           tuple(sorted(x)) for x in pr if x[0] != x[1]).most_common(8)]}
    summary = {
        "n_issues": len(issues), "n_coded": len(coded), "missing": missing, "invalid_category": bad,
        "n_papers": n_papers, "papers_with_any_major_issue": len({x["paper"] for x in issues.values()}),
        "categories": rows,
        "supergroup_paper_share": {k: round(len(v) / n_papers, 3) for k, v in sg.items()},
        "agreement": {
            "n": len(pairs),
            "primary_kappa_and_raw": kappa(pairs) if pairs else None,
            "supergroup_kappa_and_raw": kappa(sg_pairs) if sg_pairs else None,
            "primary_or_secondary_match": round(lenient / len(pairs), 2) if pairs else None,
            "top_confusions": [[a, b, n] for (a, b), n in confusions.most_common(8)],
        },
        "cross_family_agreement": cross,
        "confidence": dict(collections.Counter(c["confidence"] for c in coded.values())),
    }
    (T / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")

    # Candidate cases: high-confidence codings, agreed by the recoder when
    # recoded, at most one per paper within a category.
    rng = random.Random(7)
    lines = ["# Candidate cases per category (private: names papers)", "",
             "Each case is a referee-identified major issue to check against the paper before it",
             "informs a composite example in the essay.", ""]
    for r in rows:
        pool = [i for i, c in coded.items() if c["primary"] == r["id"] and c["confidence"] == "high"
                and (i not in recoded or recoded[i]["primary"] == r["id"])]
        rng.shuffle(pool)
        pool.sort(key=lambda i: i not in recoded)  # double-coded first
        chosen, seen = [], set()
        for i in pool:
            if issues[i]["paper"] not in seen:
                chosen.append(i)
                seen.add(issues[i]["paper"])
            if len(chosen) == 3:
                break
        lines += [f"## {r['name']} (`{r['id']}`; {r['issues']} issues, {r['paper_share']:.0%} of papers)", "",
                  cats[r["id"]]["definition"], ""]
        for i in chosen:
            x = issues[i]
            lines.append(f"- [{x['paper']}](https://arxiv.org/abs/{x['paper']}) {x['title']}  ")
            lines.append(f"  Issue: {x['issue']}{' (double-coded)' if i in recoded else ''}  ")
            lines.append(f"  Review: [reviews-v2/{x['paper']}.md](../reviews-v2/{x['paper']}.md)")
        lines.append("")
    (T / "candidates.md").write_text("\n".join(lines))

    print(json.dumps({k: v for k, v in summary.items() if k != "categories"}, indent=1))
    print(f"{'category':32}{'issues':>7}{'papers':>8}{'Apr-Jun':>9}{'Jul-Oct':>9}{'proof':>7}{'rest':>7}")
    for r in rows:
        print(f"{r['id']:32}{r['issues']:>7}{r['paper_share']:>8.0%}{r['paper_share_apr_jun']:>9.0%}"
              f"{r['paper_share_jul_oct']:>9.0%}{r['paper_share_proof']:>7.0%}{r['paper_share_rest']:>7.0%}")


if __name__ == "__main__":
    main()
