"""Compare the AI referee's verdicts on the control sample with those on the AI papers.

    REVIEW_WORK=/path/to/private/work python3 -I review/scripts/control_compare.py

Reads the control reviews (reviews-control/*.md, written with the unchanged review-v2 prompt in one shuffled
batch), the original reviews (v2_records.json) and review/control/sample.json. Three comparisons:
- controls against the 130 reviewed AI papers with a cond-mat or quant-ph primary category (original reviews);
- the 20 re-reviewed AI papers, new against original reviews (drift of the referee between the two runs);
- controls against those 20 re-reviews (same batch, so free of drift, but small).
Intervals are 95% bootstrap intervals over papers (differences: resampling each group independently).
Writes control_compare.json into REVIEW_WORK; it holds aggregates only.
"""

import json
import os
import random
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
# The unpublished review data live outside this repository (see review/README.md).
HERE = Path(os.environ.get("REVIEW_WORK", REPO / "review" / "work")).resolve()
LEVEL = {"none": 0, "mild": 1, "substantial": 2, "severe": 3}
BOOT, SEED = 4000, 1

METRICS = {
    "share_with_major_issue": lambda r: float(r["n_major"] > 0),
    "mean_major_issues": lambda r: float(r["n_major"]),
    "reproducibility": lambda r: float(r["reproducibility"]),
    "writing_quality": lambda r: float(r["writing_quality"]),
    "claims_match_evidence": lambda r: float(r["claims_match_evidence"]),
    "share_substantial_or_severe_overclaiming": lambda r: float(r["overclaiming"] in ("substantial", "severe")),
    "share_new_result_claimed": lambda r: float(r["new_scientific_result"] != "none"),
    "share_new_result_validated": lambda r: float(r["new_scientific_result"] == "claimed and independently validated"),
    "share_with_code_link": lambda r: float(bool(r["code_urls"])),
}


def review_json(path):
    blocks = re.findall(r"```json\s*(\{.*?\})\s*```", path.read_text(), re.S)
    j = json.loads(blocks[-1])
    return {"id": j["arxiv_id"], "reproducibility": j["reproducibility"], "writing_quality": j["writing_quality"],
            "claims_match_evidence": j["claims_match_evidence"], "overclaiming": j["overclaiming"],
            "n_major": len(j["major_issues"]), "new_scientific_result": j["new_scientific_result"],
            "code_urls": j.get("code_urls") or [], "ai_use_statement": j.get("ai_use_statement"),
            "models": j.get("models") or []}


def mean(xs):
    return sum(xs) / len(xs)


def describe(recs, rng):
    out = {"n": len(recs)}
    for name, f in METRICS.items():
        xs = [f(r) for r in recs]
        boots = sorted(mean([rng.choice(xs) for _ in xs]) for _ in range(BOOT))
        out[name] = {"value": round(mean(xs), 3), "lo": round(boots[int(0.025 * BOOT)], 3),
                     "hi": round(boots[int(0.975 * BOOT)], 3)}
    return out


def difference(a, b, rng, paired=False):
    """b minus a, per metric, with a bootstrap interval."""
    out = {}
    for name, f in METRICS.items():
        xa, xb = [f(r) for r in a], [f(r) for r in b]
        if paired:
            d = [y - x for x, y in zip(xa, xb)]
            boots = sorted(mean([rng.choice(d) for _ in d]) for _ in range(BOOT))
            value = mean(d)
        else:
            boots = sorted(mean([rng.choice(xb) for _ in xb]) - mean([rng.choice(xa) for _ in xa]) for _ in range(BOOT))
            value = mean(xb) - mean(xa)
        out[name] = {"value": round(value, 3), "lo": round(boots[int(0.025 * BOOT)], 3),
                     "hi": round(boots[int(0.975 * BOOT)], 3)}
    return out


def main():
    rng = random.Random(SEED)
    sample = json.loads((REPO / "review" / "control" / "sample.json").read_text())
    control_ids = [s["arxiv_id"] for s in sample["sample"]]
    rereview_ids = sample["rereview"]["ids"]
    new = {p.stem: review_json(p) for p in sorted((HERE / "reviews-control").glob("*.md"))}
    missing = [i for i in control_ids + rereview_ids if i not in new]
    original = {r["id"]: r for r in json.loads((HERE / "v2_records.json").read_text())}
    arxiv = {r["arxiv_id"]: r for r in json.loads((REPO / "corpus" / "arxiv.json").read_text())}
    phys = [i for i in original if arxiv[i]["categories"][0].startswith("cond-mat") or arxiv[i]["categories"][0] == "quant-ph"]
    controls = [new[i] for i in control_ids if i in new]
    ai_phys = [original[i] for i in phys]
    re_new = [new[i] for i in rereview_ids if i in new]
    re_old = [original[i] for i in rereview_ids if i in new]
    out = {
        "missing_reviews": missing,
        "controls_mentioning_models": sum(bool(r["models"]) for r in controls),
        "groups": {"control": describe(controls, rng), "ai_physics_original": describe(ai_phys, rng),
                   "ai_rereview_new": describe(re_new, rng), "ai_rereview_original": describe(re_old, rng),
                   "ai_all_original": describe(list(original.values()), rng)},
        "differences": {
            "control_minus_ai_physics": difference(ai_phys, controls, rng),
            "rereview_new_minus_original": difference(re_old, re_new, rng, paired=True),
            "control_minus_rereview_new": difference(re_new, controls, rng),
        },
    }
    (HERE / "control_compare.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "groups"}, indent=1)[:3000])


if __name__ == "__main__":
    main()
