"""Aggregate the prompt-v2 full-text reviews into summary statistics.

Writes v2_records.json (one flat record per paper) and v2_summary.json, and
prints a readable summary. Scopes and uses come from the title/abstract
classification; everything else comes from the reviews.
"""

import collections
import csv
import os
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
# Working directory of the review run (reviews, records and intermediate files);
# set REVIEW_WORK to point elsewhere. Its contents are not published.
HERE = Path(os.environ.get("REVIEW_WORK", REPO / "review" / "work")).resolve()
CLASSIFIED = REPO / "classification" / "classified.csv"
FRAME = json.loads((HERE / "full_frame.json").read_text())["records"]
SAMPLE_IDS = [s["native_id"] for s in json.loads((HERE / "sample.json").read_text())["sample"]]


def review_json(path):
    blocks = re.findall(r"```json\s*(\{.*?\})\s*```", path.read_text(), re.S)
    return json.loads(blocks[-1]) if blocks else None


def scope_group(row):
    scopes = {row["scope"], *json.loads(row["application_scopes"] or "[]")}
    if "condensed-matter" in scopes:
        return "condensed-matter"
    if "materials-science" in scopes:
        return "materials-science"
    if row["scope"] == "adjacent-quantum":
        return "adjacent-quantum"
    return "other"


def frac(items, pred):
    items = list(items)
    return round(sum(1 for x in items if pred(x)) / len(items), 3) if items else None


def summarize(recs):
    n = len(recs)
    out = {"n": n}
    for k in ("reproducibility", "writing_quality", "claims_match_evidence"):
        vals = sorted(r[k] for r in recs)
        out[k] = {"mean": round(sum(vals) / n, 2), "median": vals[n // 2],
                  "dist": dict(sorted(collections.Counter(vals).items()))}
    out["overclaiming"] = dict(collections.Counter(r["overclaiming"] for r in recs))
    out["share_substantial_or_severe"] = frac(recs, lambda r: r["overclaiming"] in ("substantial", "severe"))
    out["share_with_major_issue"] = frac(recs, lambda r: r["n_major"] > 0)
    out["mean_major_issues"] = round(sum(r["n_major"] for r in recs) / n, 2)
    out["harness"] = dict(collections.Counter(r["harness_class"] for r in recs))
    out["repeated_runs"] = dict(collections.Counter(r["repeated_runs"] for r in recs))
    out["human_intervention"] = dict(collections.Counter(r["human_intervention"] for r in recs))
    out["new_scientific_result"] = dict(collections.Counter(r["new_scientific_result"] for r in recs))
    out["share_variance_reported"] = frac(recs, lambda r: r["variance_reported"])
    out["share_cost_reported"] = frac(recs, lambda r: r["cost_reported"])
    out["share_code_url_given"] = frac(recs, lambda r: r["n_code_urls"] > 0)
    out["share_any_dated_system_snapshot"] = frac(recs, lambda r: r["dated_system_snapshot"])
    out["share_evaluation_dates_stated"] = frac(recs, lambda r: r["eval_dates_stated"])
    out["share_single_base_model"] = frac(recs, lambda r: r["base_models"] == 1)
    out["share_ai_use_statement"] = frac(recs, lambda r: r["ai_use_statement"])
    return out


def main():
    classified = {r["native_id"]: r for r in csv.DictReader(CLASSIFIED.open()) if r["provider"] == "arxiv"}
    recs, missing = [], []
    for f in FRAME:
        pid = f["native_id"]
        path = HERE / "reviews-v2" / f"{pid}.md"
        j = review_json(path) if path.exists() else None
        if j is None:
            missing.append(pid)
            continue
        c = classified[pid]
        system = [m for m in j["models"] if isinstance(m, dict) and m.get("role") == "system"]
        harness = str(j["harness"])
        recs.append({
            "id": pid, "date": f["date"][:10], "title": f["title"],
            "scope_group": scope_group(c), "use": c["use"], "kind": c["kind"],
            "reproducibility": j["reproducibility"], "writing_quality": j["writing_quality"],
            "claims_match_evidence": j["claims_match_evidence"], "overclaiming": j["overclaiming"],
            "n_major": len(j["major_issues"]), "major_issues": j["major_issues"],
            "minor": j["minor_issue_count"],
            "harness": harness,
            "harness_class": ("off-the-shelf" if "off-the-shelf" in harness
                              else "custom" if harness.startswith("custom") else harness),
            "base_models": j["base_models_in_system_role"],
            "system_models": [m.get("name") for m in system],
            "all_models": [(m.get("name"), m.get("version"), m.get("role")) for m in j["models"] if isinstance(m, dict)],
            "dated_system_snapshot": any(m.get("dated_snapshot") for m in system),
            "eval_dates_stated": "not stated" not in str(j["evaluation_dates"]).lower(),
            "evaluation_dates": j["evaluation_dates"],
            "repeated_runs": j["repeated_runs"], "variance_reported": j["variance_reported"],
            "cost_reported": j["cost_reported"], "human_intervention": j["human_intervention"],
            "new_scientific_result": j["new_scientific_result"],
            "n_code_urls": len(j["code_urls"]), "code_urls": j["code_urls"],
            "ai_use_statement": j["ai_use_statement"],
        })
    summary = {"overall": summarize(recs), "missing": missing}
    for key in ("scope_group", "kind", "human_intervention"):
        groups = collections.defaultdict(list)
        for r in recs:
            groups[r[key]].append(r)
        summary[f"by_{key}"] = {g: summarize(v) for g, v in sorted(groups.items()) if len(v) >= 5}
    proof = [r for r in recs if r["use"] == "reasoning-proof"]
    rest = [r for r in recs if r["use"] != "reasoning-proof"]
    summary["reasoning_proof_vs_rest"] = {"reasoning-proof": summarize(proof), "rest": summarize(rest)}
    names = collections.Counter(r["harness"].split("off-the-shelf:")[1].strip()
                                for r in recs if "off-the-shelf:" in r["harness"])
    summary["off_the_shelf_harnesses"] = dict(names.most_common())

    # Prompt v1 versus v2 on the original 20-paper sample.
    comp = []
    for pid in SAMPLE_IDS:
        v1 = [review_json(HERE / d / f"{pid}.md") for d in ("reviews", "reviews-retest")]
        v2 = next((r for r in recs if r["id"] == pid), None)
        if v2 and all(v1):
            comp.append({"id": pid, "v1": [x["overclaiming"] for x in v1], "v2": v2["overclaiming"],
                         "claims_v1": [x["claims_match_evidence"] for x in v1], "claims_v2": v2["claims_match_evidence"]})
    lvl = {"none": 0, "mild": 1, "substantial": 2, "severe": 3}
    summary["prompt_v1_vs_v2"] = {
        "n": len(comp),
        "v1_substantial_share": frac(comp, lambda c: c["v1"][0] in ("substantial", "severe")),
        "v1_retest_substantial_share": frac(comp, lambda c: c["v1"][1] in ("substantial", "severe")),
        "v2_substantial_share": frac(comp, lambda c: c["v2"] in ("substantial", "severe")),
        "mean_overclaim_level_v1": round(sum(lvl[c["v1"][0]] + lvl[c["v1"][1]] for c in comp) / (2 * len(comp)), 2) if comp else None,
        "mean_overclaim_level_v2": round(sum(lvl[c["v2"]] for c in comp) / len(comp), 2) if comp else None,
        "mean_claims_v1": round(sum(sum(c["claims_v1"]) for c in comp) / (2 * len(comp)), 2) if comp else None,
        "mean_claims_v2": round(sum(c["claims_v2"] for c in comp) / len(comp), 2) if comp else None,
        "papers": comp,
    }
    (HERE / "v2_records.json").write_text(json.dumps(recs, indent=1, ensure_ascii=False) + "\n")
    (HERE / "v2_summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "prompt_v1_vs_v2"}, indent=1)[:6000])
    pv = summary["prompt_v1_vs_v2"]
    print({k: v for k, v in pv.items() if k != "papers"})


if __name__ == "__main__":
    main()
