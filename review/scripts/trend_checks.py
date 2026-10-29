"""Time trend of the review scores, overall and within strata, and the
correlation of model lag with the scores.

Spearman correlations use average ranks for ties; p-values come from 5000
random permutations.
"""

import collections
import os
import json
import random
import statistics
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
# Working directory of the review run (reviews, records and intermediate files);
# set REVIEW_WORK to point elsewhere. Its contents are not published.
HERE = Path(os.environ.get("REVIEW_WORK", REPO / "review" / "work")).resolve()
LEVEL = {"none": 0, "mild": 1, "substantial": 2, "severe": 3}


def ranks(v):
    order = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2
        i = j + 1
    return r


def pearson(a, b):
    ma, mb = statistics.fmean(a), statistics.fmean(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    den = (sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b)) ** 0.5
    return num / den if den else 0.0


def spearman(a, b, n_perm=5000, rng=random.Random(0)):
    ra, rb = ranks(a), ranks(b)
    rho = pearson(ra, rb)
    rb = list(rb)
    hits = 0
    for _ in range(n_perm):
        rng.shuffle(rb)
        hits += abs(pearson(ra, rb)) >= abs(rho) - 1e-12
    return {"rho": round(rho, 2), "p": round((hits + 1) / (n_perm + 1), 4), "n": len(a)}


def metrics(r):
    return {"claims_match_evidence": r["claims_match_evidence"], "writing_quality": r["writing_quality"],
            "reproducibility": r["reproducibility"], "overclaiming": LEVEL[r["overclaiming"]]}


def trend(recs):
    dates = [int(r["date"].replace("-", "")) for r in recs]
    return {m: spearman(dates, [metrics(r)[m] for r in recs]) for m in metrics(recs[0])}


def main():
    recs = json.loads((HERE / "v2_records.json").read_text())
    strata = {
        "all": recs,
        "non-proof": [r for r in recs if r["use"] != "reasoning-proof"],
        "no AI-use statement": [r for r in recs if not r["ai_use_statement"]],
        "AI-use statement": [r for r in recs if r["ai_use_statement"]],
        **{f"kind={k}": [r for r in recs if r["kind"] == k] for k in ("application", "method", "benchmark")},
    }
    out = {"trend": {name: trend(sel) for name, sel in strata.items()}}
    months = collections.defaultdict(list)
    for r in recs:
        months[r["date"][:7]].append(r)
    out["by_month"] = {m: {"n": len(v),
                           "share_proof": round(sum(r["use"] == "reasoning-proof" for r in v) / len(v), 2),
                           "share_ai_use_statement": round(sum(r["ai_use_statement"] for r in v) / len(v), 2),
                           "mean_claims": round(statistics.fmean(r["claims_match_evidence"] for r in v), 2)}
                       for m, v in sorted(months.items())}
    lag = [x for x in json.loads((HERE / "model_lag.json").read_text())["papers"] if x["lag_days"] >= 0]
    by_id = {r["id"]: r for r in recs}
    days = [x["lag_days"] for x in lag]
    out["lag_vs_date"] = spearman([int(x["date"].replace("-", "")) for x in lag], days)
    out["lag_vs_scores"] = {m: spearman(days, [metrics(by_id[x["id"]])[m] for x in lag]) for m in metrics(recs[0])}
    (HERE / "trend_checks.json").write_text(json.dumps(out, indent=1) + "\n")
    for name, res in out["trend"].items():
        print(f"{name:22}", "  ".join(f"{m[:9]} {v['rho']:+.2f} (p={v['p']:.3f})" for m, v in res.items()), f"n={res['claims_match_evidence']['n']}")
    for m, v in out["by_month"].items():
        print(m, v)
    print("lag vs date", out["lag_vs_date"])
    print("lag vs scores", out["lag_vs_scores"])


if __name__ == "__main__":
    main()
