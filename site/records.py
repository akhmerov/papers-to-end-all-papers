"""Assemble the per-paper data of the dashboard from the public files.

Joins, for each of the 228 papers: arXiv metadata (corpus/arxiv.json), the title/abstract labels
(classification/classified.json), the field and question codes (classification/subjects/coded-*.json)
and the factual fields of the full-text review (review/data/papers.json). No referee score, issue or
verdict is included: those are not public.
"""

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SUBJ = REPO / "classification" / "subjects"

# Developer of a model, from its name as reported by the referee.
FAMILIES = [
    (r"\b(gpt|chatgpt|o[134](-mini|-pro)?\b|codex|davinci)", "OpenAI"),
    (r"claude|opus|sonnet|haiku|fable", "Anthropic"),
    (r"gemini|gemma|palm|bard", "Google"),
    (r"llama", "Meta"),
    (r"qwen|qwq", "Qwen"),
    (r"deepseek", "DeepSeek"),
    (r"mistral|mixtral|ministral|magistral|devstral|codestral", "Mistral"),
    (r"grok", "xAI"),
    (r"kimi", "Moonshot"),
    (r"\bglm|chatglm", "Zhipu"),
    (r"\bphi-?\d", "Microsoft"),
]


def family(name):
    low = name.lower()
    for pattern, fam in FAMILIES:
        if re.search(pattern, low):
            return fam
    return None


def load(path):
    return json.loads((REPO / path).read_text())


def coded(axis, coder):
    return {c["id"]: c[axis] for c in json.loads((SUBJ / f"coded-{axis}-{coder}.json").read_text())}


def both(a, b):
    """Codes of the two coders, Sol first; one entry when they agree."""
    return [a] if a == b else [a, b]


def records():
    classified = {r["id"]: r for r in load("classification/classified.json")}
    arxiv = {r["arxiv_id"]: r for r in load("corpus/arxiv.json")}
    field = {c: coded("field", c) for c in ("sol", "opus")}
    question = {c: coded("question", c) for c in ("sol", "opus")}
    qgroup = {c["id"]: c["supergroup"] for c in json.loads((SUBJ / "codebook-question.json").read_text())["categories"]}

    out = []
    for rev in load("review/data/papers.json"):
        uid = "arxiv:" + rev["id"]
        r, meta = classified[uid], arxiv[rev["id"]]
        system = sorted({m["name"] for m in rev["models"] if m["role"] == "system"})
        q = both(question["sol"][uid], question["opus"][uid])
        out.append({
            "id": uid,
            "date": r["date"][:10],
            "title": r["title"],
            "authors": meta.get("authors") or [],
            "abstract": r.get("abstract") or "",  # arXiv metadata, CC0
            "url": r["url"],
            "doi": r.get("doi") or None,
            "category": meta["categories"][0],
            "scope": r["scope"],
            "use": r["use"],
            "kind": r["kind"],
            "agent_form": r["agent_form"],
            "field": both(field["sol"][uid], field["opus"][uid]),
            "question": q,
            "physical_world": [qgroup[x] == "physical-world" for x in q],
            "models": system,
            "families": sorted({f for m in system if (f := family(m))}),
            "harness": rev["harness"],
            "code_urls": rev["code_urls"],
            "ai_use_statement": rev["ai_use_statement"],
            "model_lag_days": (rev.get("model_lag") or {}).get("lag_days"),
        })
    out.sort(key=lambda x: x["date"], reverse=True)
    return out


def codebooks():
    """Category names of the field and question axes, in display order."""
    field = json.loads((SUBJ / "codebook-field.json").read_text())
    question = json.loads((SUBJ / "codebook-question.json").read_text())
    return {
        "field": [{"id": c["id"], "name": c["name"], "group": field["supergroups"][c["supergroup"]]}
                  for c in field["categories"]],
        "question": [{"id": c["id"], "name": c["name"], "physical_world": c["supergroup"] == "physical-world"}
                     for c in question["categories"]],
    }


if __name__ == "__main__":
    recs = records()
    print(len(recs), "papers;", sum(bool(r["authors"]) for r in recs), "with authors")
