"""Draw the control sample: random cond-mat and quant-ph preprints from the window that do not use language models.

    python3 -I review/control/sample.py      # network: arXiv API, about 3 s per request

The control calibrates the AI referee: the same prompt and model review ordinary papers from the same
categories and months. Its primary-category mix matches the 130 reviewed papers whose primary category is
cond-mat or quant-ph. A draw is rejected when its primary category differs from the stratum, when its title
or abstract contains any language-model, agent or harness term of the corpus protocol (corpus/protocol.json),
or when it is already in the corpus. The sample size (50) was fixed before any control paper was reviewed.
Writes sample.json, with every draw and the reason it was rejected.
"""

import json
import random
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
API = "https://export.arxiv.org/api/query"
ATOM = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom",
        "os": "http://a9.com/-/spec/opensearch/1.1/"}
# Primary-category quotas, proportional to the reviewed papers with a cond-mat or quant-ph primary category
# (mtrl-sci 63, quant-ph 57, and 10 in four other cond-mat categories).
QUOTAS = {"cond-mat.mtrl-sci": 24, "quant-ph": 22, "cond-mat.mes-hall": 1, "cond-mat.stat-mech": 1,
          "cond-mat.soft": 1, "cond-mat.str-el": 1}
SEED = 20261030
WINDOW = ("202604180000", "202610182359")


# The API does not page beyond 10 000 results, so the window is split into months; a draw picks a month in
# proportion to its count and then a uniform position within it, which is uniform over the window.
MONTHS = [("202604180000", "202604302359"), ("202605010000", "202605312359"), ("202606010000", "202606302359"),
          ("202607010000", "202607312359"), ("202608010000", "202608312359"), ("202609010000", "202609302359"),
          ("202610010000", "202610182359")]


def query(category, start, n=1, window=WINDOW):
    params = {"search_query": f"cat:{category} AND submittedDate:[{window[0]} TO {window[1]}]",
              "start": start, "max_results": n, "sortBy": "submittedDate", "sortOrder": "ascending"}
    for attempt in range(5):
        try:
            with urllib.request.urlopen(f"{API}?{urllib.parse.urlencode(params)}", timeout=60) as resp:
                root = ET.fromstring(resp.read())
            time.sleep(3)
            return root
        except OSError:
            time.sleep(10 * (attempt + 1))
    raise RuntimeError(f"arXiv API unavailable for {category} at {start}")


def entry(e):
    arxiv_id = e.find("a:id", ATOM).text.rsplit("/", 1)[-1]
    return {"arxiv_id": re.sub(r"v\d+$", "", arxiv_id),
            "title": " ".join(e.find("a:title", ATOM).text.split()),
            "abstract": " ".join(e.find("a:summary", ATOM).text.split()),
            "primary": e.find("arxiv:primary_category", ATOM).attrib["term"],
            "published": e.find("a:published", ATOM).text[:10]}


def main():
    terms = [t for family in json.loads((REPO / "corpus" / "protocol.json").read_text())["terms"].values() for t in family]
    pattern = re.compile(r"\b(" + "|".join(re.escape(t) for t in terms) + r")\b", re.I)
    corpus = {r["arxiv_id"] for r in json.loads((REPO / "corpus" / "arxiv.json").read_text())}
    rng = random.Random(SEED)
    draws, sample, counts_all = [], [], {}
    for category, quota in QUOTAS.items():
        counts = [int(query(category, 0, window=m).find("os:totalResults", ATOM).text) for m in MONTHS]
        total = sum(counts)
        counts_all[category] = dict(zip((m[0][:6] for m in MONTHS), counts))
        seen, kept = set(), 0
        while kept < quota:
            pos = rng.randrange(total)
            if pos in seen:
                continue
            seen.add(pos)
            month = 0
            while pos - sum(counts[:month]) >= counts[month]:
                month += 1
            start = pos - sum(counts[:month])
            found = query(category, start, window=MONTHS[month]).findall("a:entry", ATOM)
            if not found:
                draws.append({"stratum": category, "month": MONTHS[month][0][:6], "start": start, "rejected": "empty result"})
                continue
            rec = entry(found[0])
            reason = ("other primary category" if rec["primary"] != category
                      else "language-model term" if pattern.search(rec["title"] + " " + rec["abstract"])
                      else "in corpus" if rec["arxiv_id"] in corpus
                      else "duplicate" if rec["arxiv_id"] in {s["arxiv_id"] for s in sample} else None)
            draws.append({"stratum": category, "month": MONTHS[month][0][:6], "start": start, "arxiv_id": rec["arxiv_id"],
                          "rejected": reason})
            if reason is None:
                sample.append({"arxiv_id": rec["arxiv_id"], "stratum": category, "published": rec["published"],
                               "title": rec["title"]})
                kept += 1
        print(category, total, "records in window;", kept, "kept of", len(seen), "draws")
    (HERE / "sample.json").write_text(json.dumps(
        {"seed": SEED, "window": WINDOW, "quotas": QUOTAS, "counts": counts_all, "sample": sample, "draws": draws},
        indent=1, ensure_ascii=False) + "\n")
    print(len(sample), "control papers")


if __name__ == "__main__":
    main()
