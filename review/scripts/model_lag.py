"""Model-to-paper lag: how old is the newest model a paper actually ran?

For each paper, take the general-purpose LLMs it used in any role except
writing (system, baseline, judge, data generation, other), look up their
release dates in model-dates/dates-*.json, and compute

  lag          = first arXiv version date - release date of the newest model,
  frontier gap = release of the newest frontier flagship available at the
                 paper date - release of the newest model used.

Release dates are lower bounds on when a model could have been evaluated, and
reviewers read the latest arXiv version, so models added in revisions can give
a negative lag; those papers are listed separately.
"""

import collections
import datetime as dt
import os
import json
import statistics
from pathlib import Path

from model_names import paper_models

REPO = Path(__file__).resolve().parents[2]
# Working directory of the review run (reviews, records and intermediate files);
# set REVIEW_WORK to point elsewhere. Its contents are not published.
HERE = Path(os.environ.get("REVIEW_WORK", REPO / "review" / "work")).resolve()
GENERAL = ("frontier-api", "open-weights")

# Entries the lookup left undated although the paper used a real model.
# "GPT-6" without a tier gets the first GPT-6 release (an upper bound on the
# lag); Pro is a compute mode of Astra; Mythos 5 was usable by vetted partners
# from its announcement.
DATE_OVERRIDES = {
    "gpt-6": "2026-09-04", "chat-gpt-6": "2026-09-04", "gpt-6-astra-pro": "2026-09-04",
    "claude-mythos-5": "2026-06-09",
}


def day(s):
    return dt.date.fromisoformat(s[:10])


def quartiles(xs):
    xs = sorted(xs)
    if len(xs) < 4:
        return None
    q = statistics.quantiles(xs, n=4)
    return {"n": len(xs), "q1": q[0], "median": statistics.median(xs), "q3": q[2]}


def main():
    dates, frontier = {}, []
    for part in "abc":
        path = REPO / "review" / "data" / "model-dates" / f"dates-{part}.json"
        data = json.loads(path.read_text())
        for m in data["models"]:
            if m["key"] in DATE_OVERRIDES:
                m = {**m, "class": "frontier-api", "release_date": DATE_OVERRIDES[m["key"]]}
            dates[m["key"]] = m
        frontier += data.get("frontier", [])
    frontier = sorted((day(f["release_date"]), f["vendor"], f["model"]) for f in frontier if f.get("release_date"))
    us_frontier = [f for f in frontier if f[1].lower().split()[0] in ("openai", "anthropic", "google", "xai", "x.ai")]

    recs = json.loads((HERE / "v2_records.json").read_text())
    rows, undated = [], collections.Counter()
    for r in recs:
        if r["kind"] == "review-perspective":  # models are cited, not run
            continue
        paper_date = day(r["date"])
        used = []
        for key, role in paper_models(r):
            m = dates.get(key)
            if not m or m["class"] not in GENERAL:
                continue
            if not m.get("release_date"):
                undated[key] += 1
                continue
            used.append((day(m["release_date"]), key, role, m["class"]))
        if not used:
            continue
        system = [u for u in used if u[2] == "system"]
        newest = max(used)
        avail = [f for f in us_frontier if f[0] <= paper_date]
        rows.append({
            "id": r["id"], "date": r["date"], "use": r["use"], "kind": r["kind"],
            "newest_model": newest[1], "newest_release": newest[0].isoformat(), "newest_class": newest[3],
            "lag_days": (paper_date - newest[0]).days,
            "system_lag_days": (paper_date - max(system)[0]).days if system else None,
            "newest_system_model": max(system)[1] if system else None,
            "frontier_at_paper": f"{avail[-1][2]} ({avail[-1][0]})" if avail else None,
            "frontier_gap_days": (avail[-1][0] - newest[0]).days if avail else None,
            "flagship_releases_since": len({f[0] for f in avail if f[0] > newest[0]}),
            "n_models": len({u[1] for u in used}),
        })
    ok = [x for x in rows if x["lag_days"] >= 0]
    neg = [x for x in rows if x["lag_days"] < 0]
    summary = {
        "n_papers_with_dated_model": len(rows),
        "lag_days_any_role": quartiles([x["lag_days"] for x in ok]),
        "lag_days_system_role": quartiles([x["system_lag_days"] for x in ok if x["system_lag_days"] is not None]),
        "frontier_gap_days": quartiles([max(x["frontier_gap_days"], 0) for x in ok if x["frontier_gap_days"] is not None]),
        "flagship_releases_since": quartiles([x["flagship_releases_since"] for x in ok]),
        "share_newest_is_frontier_api": round(sum(x["newest_class"] == "frontier-api" for x in ok) / len(ok), 3),
        "share_lag_over_180d": round(sum(x["lag_days"] > 180 for x in ok) / len(ok), 3),
        "share_lag_over_365d": round(sum(x["lag_days"] > 365 for x in ok) / len(ok), 3),
        "share_using_current_frontier": round(sum((x["frontier_gap_days"] or 0) <= 0 for x in ok) / len(ok), 3),
        "by_month": {},
        "negative_lag": [{k: x[k] for k in ("id", "date", "newest_model", "newest_release")} for x in neg],
        "undated_general_models": dict(undated.most_common()),
    }
    months = collections.defaultdict(list)
    for x in ok:
        months[x["date"][:7]].append(x)
    for mo, xs in sorted(months.items()):
        summary["by_month"][mo] = {"lag": quartiles([x["lag_days"] for x in xs]),
                                   "frontier_gap": quartiles([max(x["frontier_gap_days"] or 0, 0) for x in xs])}
    (HERE / "model_lag.json").write_text(json.dumps({"summary": summary, "frontier": [
        {"date": d.isoformat(), "vendor": v, "model": m} for d, v, m in frontier], "papers": rows}, indent=1) + "\n")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
