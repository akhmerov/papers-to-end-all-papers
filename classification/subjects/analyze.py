"""Field and question shares of the 228 papers, from two independent coders.

    pixi run agreement

Reads the codebooks, papers.jsonl and the codes of the two coders (coded-{field,question}-{sol,opus}.json).
Writes summary.json.

Shares are the mean of the two coders' shares; the interval is a bootstrap over papers (95%), so it
carries sampling noise and coder disagreement together.
"""

import collections
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
CODERS = ("sol", "opus")
BOOT, SEED = 2000, 1


def kappa(pairs):
    n = len(pairs)
    po = sum(a == b for a, b in pairs) / n
    ca, cb = collections.Counter(a for a, _ in pairs), collections.Counter(b for _, b in pairs)
    pe = sum(ca[k] * cb[k] for k in ca) / n ** 2
    return {"n": n, "kappa": round((po - pe) / (1 - pe), 2), "raw": round(po, 2)}


def shares(ids, codes, key):
    """Mean share over the coders of each value of key(coder, id), with a bootstrap interval over papers."""
    cats = sorted({key(c, i) for c in CODERS for i in ids})

    def point(sample):
        cnt = collections.Counter(key(c, i) for c in CODERS for i in sample)
        return {k: cnt[k] / (len(sample) * len(CODERS)) for k in cats}

    est = point(ids)
    rng = random.Random(SEED)
    draws = [point([rng.choice(ids) for _ in ids]) for _ in range(BOOT)]
    out = {}
    for k in cats:
        v = sorted(d[k] for d in draws)
        out[k] = {"share": round(est[k], 3), "lo": round(v[int(0.025 * BOOT)], 3), "hi": round(v[int(0.975 * BOOT)], 3)}
    return dict(sorted(out.items(), key=lambda kv: -kv[1]["share"]))


def main():
    ids = [json.loads(line)["id"] for line in (HERE / "papers.jsonl").read_text().splitlines()]
    books = {axis: {c["id"]: c for c in json.loads((HERE / f"codebook-{axis}.json").read_text())["categories"]}
             for axis in ("field", "question")}
    codes = {}
    for axis in ("field", "question"):
        for coder in CODERS:
            coded = {c["id"]: c[axis] for c in json.loads((HERE / f"coded-{axis}-{coder}.json").read_text())}
            assert sorted(coded) == sorted(ids), (axis, coder)
            assert set(coded.values()) <= set(books[axis]), (axis, coder)
            for i, v in coded.items():
                codes.setdefault(coder, {}).setdefault(i, {})[axis] = v
    group = {axis: (lambda v, a=axis: books[a][v]["supergroup"]) for axis in books}
    out = {"n": len(ids), "coders": {"sol": "GPT-6.1 Sol", "opus": "Claude Opus 5.5"}, "agreement": {}}
    for axis in ("field", "question"):
        out["agreement"][axis] = kappa([(codes["sol"][i][axis], codes["opus"][i][axis]) for i in ids])
        out["agreement"][axis + "_supergroup"] = kappa(
            [(group[axis](codes["sol"][i][axis]), group[axis](codes["opus"][i][axis])) for i in ids])
        out[axis + "_shares"] = shares(ids, codes, lambda c, i, a=axis: codes[c][i][a])
        out[axis + "_supergroup_shares"] = shares(ids, codes, lambda c, i, a=axis: group[a](codes[c][i][a]))
    # Each field split by whether the question is about the physical world, pairing the field and question
    # codes of the same coder; the two parts add up to the field's share.
    split = shares(ids, codes, lambda c, i: (codes[c][i]["field"], group["question"](codes[c][i]["question"])))
    out["field_by_question_supergroup"] = {
        f: {q: split.get((f, q), {"share": 0.0})["share"] for q in ("physical-world", "ai-workflow")}
        for f in out["field_shares"]}
    physical = collections.Counter(codes[c][i]["field"] for c in CODERS for i in ids
                                   if group["question"](codes[c][i]["question"]) == "physical-world")
    total = sum(physical.values())
    out["fields_of_physical_world_papers"] = {f: round(n / total, 3) for f, n in physical.most_common()}
    (HERE / "summary.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("n", "agreement", "field_supergroup_shares",
                                          "question_supergroup_shares", "fields_of_physical_world_papers")}, indent=1))


if __name__ == "__main__":
    main()
