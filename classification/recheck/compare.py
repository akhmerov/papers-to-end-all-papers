"""Agreement between the Haiku labels and the blind Sol recode.

Reads ../classified.json (displayed labels and the original Haiku labels), sample.json and
coded-*.json. Writes agreement.json.
"""

import collections
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
AXES = ["llm_role", "scope", "use", "kind", "agent_form", "autonomy", "breadth"]
IN_FRAME = {"substantive", "proposed"}


def kappa(pairs):
    n = len(pairs)
    po = sum(a == b for a, b in pairs) / n
    ca, cb = collections.Counter(a for a, _ in pairs), collections.Counter(b for _, b in pairs)
    pe = sum(ca[k] * cb[k] for k in ca) / n ** 2
    return {"n": n, "kappa": round((po - pe) / (1 - pe), 2) if pe < 1 else None, "raw": round(po, 2)}


def main():
    recs = {r["id"]: r for r in json.loads((HERE.parent / "classified.json").read_text())}
    sample = json.loads((HERE / "sample.json").read_text())
    sol = {}
    for p in sorted(HERE.glob("coded-*.json")):
        for c in json.loads(p.read_text()):
            sol[c["id"]] = c
    inf, controls = sample["in_frame"], sample["controls"]
    ids = inf + controls
    out = {"n_recoded": len(ids), "missing": [i for i in ids if i not in sol]}
    # Displayed labels include lead-review overrides; also compare the untouched Haiku labels.
    out["agreement_displayed"] = {a: kappa([(recs[i][a], sol[i][a]) for i in ids]) for a in AXES}
    out["agreement_haiku_original"] = {
        a: kappa([(recs[i]["original_model_labels"].get(a, recs[i][a]), sol[i][a]) for i in ids]) for a in AXES}
    out["in_frame_only"] = {a: kappa([(recs[i][a], sol[i][a]) for i in inf]) for a in AXES if a != "llm_role"}
    # Frame membership: in = substantive or proposed role of a language model.
    out["frame"] = {
        "in_frame_confirmed_by_sol": sum(sol[i]["llm_role"] in IN_FRAME for i in inf),
        "in_frame_n": len(inf),
        "controls_sol_says_in": sum(sol[i]["llm_role"] in IN_FRAME for i in controls),
        "controls_n": len(controls),
        "kappa": kappa([(recs[i]["llm_role"] in IN_FRAME, sol[i]["llm_role"] in IN_FRAME) for i in ids]),
    }
    for a in ("scope", "use"):
        conf = collections.Counter((recs[i][a], sol[i][a]) for i in inf if recs[i][a] != sol[i][a])
        out[f"top_{a}_confusions"] = [[x, y, n] for (x, y), n in conf.most_common(12)]
    (HERE / "agreement.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("n_recoded", "missing", "frame", "in_frame_only")}, indent=1))


if __name__ == "__main__":
    main()
