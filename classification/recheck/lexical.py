"""LLM-free topic check: TF-IDF + NMF on titles and abstracts of the 228 papers.

Run: pixi run lexical
Writes lexical.json (top terms per topic, topic of each record, and the
stability of the topics over random restarts).
"""

import json
import re
from pathlib import Path

import numpy as np
from sklearn.decomposition import NMF
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics import adjusted_rand_score

HERE = Path(__file__).resolve().parent
# Generic AI/LLM vocabulary is shared by every record and only blurs the subject matter.
GENERIC = {
    "llm", "llms", "language", "large", "model", "models", "agent", "agents", "agentic", "ai", "gpt", "based",
    "using", "framework", "approach", "results", "paper", "study", "propose", "proposed", "present", "show",
    "demonstrate", "new", "novel", "performance", "tasks", "task", "methods", "method", "work", "intelligence",
    "artificial", "multi", "system", "systems", "data", "learning", "machine", "scientific", "research", "reasoning",
    "tool", "tools", "human", "benchmark", "evaluation", "accuracy", "existing", "challenges", "end", "time",
    "high", "level", "use", "used", "enables", "provides", "across", "including", "multimodal", "chatgpt", "openai",
}


def main(k=8, restarts=10):
    recs = {r["id"]: r for r in json.loads((HERE.parent / "classified.json").read_text())}
    ids = json.loads((HERE / "sample.json").read_text())["in_frame"]
    docs = [f"{recs[i]['title']}. {recs[i].get('abstract') or ''}" for i in ids]
    docs = [re.sub(r"\$[^$]*\$", " ", d) for d in docs]
    vec = TfidfVectorizer(stop_words=list(ENGLISH_STOP_WORDS | GENERIC), min_df=3, max_df=0.3,
                          ngram_range=(1, 2), token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z0-9\-]+\b", sublinear_tf=True)
    X = vec.fit_transform(docs)
    terms = np.array(vec.get_feature_names_out())
    labels = []
    for seed in range(restarts):
        W = NMF(n_components=k, init="nndsvdar", random_state=seed, max_iter=800).fit_transform(X)
        labels.append(W.argmax(1))
    ari = [adjusted_rand_score(labels[0], l) for l in labels[1:]]
    nmf = NMF(n_components=k, init="nndsvd", random_state=0, max_iter=800)
    W = nmf.fit_transform(X)
    topics = []
    for t in range(k):
        top = terms[np.argsort(nmf.components_[t])[::-1][:12]]
        members = [ids[j] for j in np.where(W.argmax(1) == t)[0]]
        topics.append({"topic": t, "terms": top.tolist(), "n": len(members), "ids": members})
    topics.sort(key=lambda t: -t["n"])
    out = {"k": k, "n_docs": len(ids), "n_terms": len(terms), "restart_ari_median": float(np.median(ari)),
           "restart_ari_min": float(np.min(ari)), "topics": topics}
    (HERE / "lexical.json").write_text(json.dumps(out, indent=1) + "\n")
    print(f"docs {len(ids)} terms {len(terms)} restart ARI median {np.median(ari):.2f} min {np.min(ari):.2f}")
    for t in topics:
        print(f"{t['n']:4d}  {', '.join(t['terms'][:10])}")


if __name__ == "__main__":
    import sys
    main(*(int(a) for a in sys.argv[1:]))
