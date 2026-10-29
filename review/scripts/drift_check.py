"""Compare the drift re-reviews with the original prompt-v2 reviews.

In the full run, papers were reviewed roughly in arXiv-ID order, so paper date
and review time are confounded. The drift sample re-reviews 10 early (Apr-May)
and 10 late (Sep-Oct) papers in one shuffled batch. If the early-late gap
survives in the re-reviews, it comes from the papers rather than from the
reviewer drifting during the run.
"""

import os
import json
import statistics
from pathlib import Path

from analyze_v2 import review_json

REPO = Path(__file__).resolve().parents[2]
# Working directory of the review run (reviews, records and intermediate files);
# set REVIEW_WORK to point elsewhere. Its contents are not published.
HERE = Path(os.environ.get("REVIEW_WORK", REPO / "review" / "work")).resolve()
LEVEL = {"none": 0, "mild": 1, "substantial": 2, "severe": 3}
METRICS = ("reproducibility", "writing_quality", "claims_match_evidence", "overclaiming", "n_major")


def scores(j):
    return {**{k: j[k] for k in METRICS[:3]}, "overclaiming": LEVEL[j["overclaiming"]], "n_major": len(j["major_issues"])}


def main():
    sample = json.loads((HERE / "drift_sample.json").read_text())
    rows = []
    for group in ("early", "late"):
        for pid in sample[group]:
            new = review_json(HERE / "reviews-drift" / f"{pid}.md")
            old = review_json(HERE / "reviews-v2" / f"{pid}.md")
            if new is None:
                print("missing", pid)
                continue
            rows.append({"id": pid, "group": group, "old": scores(old), "new": scores(new)})
    out = {"n": len(rows), "metrics": {}}
    print(f"{'metric':24}{'early old':>10}{'early new':>10}{'late old':>10}{'late new':>10}{'gap old':>9}{'gap new':>9}  exact/within1")
    for m in METRICS:
        res = {}
        for g in ("early", "late"):
            sel = [r for r in rows if r["group"] == g]
            res[g] = {v: round(statistics.mean(r[v][m] for r in sel), 2) for v in ("old", "new")}
        exact = sum(r["old"][m] == r["new"][m] for r in rows)
        within = sum(abs(r["old"][m] - r["new"][m]) <= 1 for r in rows)
        gap = {v: round(res["late"][v] - res["early"][v], 2) for v in ("old", "new")}
        out["metrics"][m] = {**res, "late_minus_early": gap, "exact": exact, "within_1": within}
        print(f"{m:24}{res['early']['old']:>10}{res['early']['new']:>10}{res['late']['old']:>10}{res['late']['new']:>10}"
              f"{gap['old']:>9}{gap['new']:>9}  {exact}/{within} of {len(rows)}")
    out["papers"] = rows
    (HERE / "drift_check.json").write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
