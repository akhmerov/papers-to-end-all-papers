"""Track the full review run: which papers are launched, done, or invalid.

    python3 review_queue.py next N      # next N unlaunched IDs
    python3 review_queue.py mark ID...  # record IDs as launched
    python3 review_queue.py status      # counts, in-flight IDs, invalid outputs
    python3 review_queue.py check ID... # validate review outputs
"""

import os
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
# Working directory of the review run (reviews, records and intermediate files);
# set REVIEW_WORK to point elsewhere. Its contents are not published.
HERE = Path(os.environ.get("REVIEW_WORK", REPO / "review" / "work")).resolve()
OUT = HERE / "reviews-v2"
LOG = HERE / "launched.jsonl"
IDS = [r["native_id"] for r in json.loads((HERE / "full_frame.json").read_text())["records"]]

ENUMS = {
    "overclaiming": {"none", "mild", "substantial", "severe"},
    "repeated_runs": {"none", "some", "systematic"},
    "human_intervention": {"none reported", "minor", "substantial", "unclear"},
    "new_scientific_result": {"none", "claimed", "claimed and independently validated"},
}
ROLES = {"system", "baseline", "judge", "data-generation", "writing", "other"}
SCORES = ("reproducibility", "writing_quality", "claims_match_evidence")
LISTS = ("major_issues", "models", "baselines", "code_urls")
BOOLS = ("variance_reported", "cost_reported", "ai_use_statement")


def launched():
    if not LOG.exists():
        return []
    return [json.loads(line)["id"] for line in LOG.read_text().splitlines() if line.strip()]


def problems(arxiv_id):
    path = OUT / f"{arxiv_id}.md"
    if not path.exists():
        return ["missing"]
    blocks = re.findall(r"```json\s*(\{.*?\})\s*```", path.read_text(), re.S)
    if not blocks:
        return ["no JSON block"]
    try:
        r = json.loads(blocks[-1])
    except json.JSONDecodeError as e:
        return [f"invalid JSON: {e}"]
    out = []
    if r.get("arxiv_id") != arxiv_id:
        out.append("arxiv_id mismatch")
    for k in SCORES:
        if r.get(k) not in (1, 2, 3, 4, 5):
            out.append(f"{k}={r.get(k)!r}")
    for k, allowed in ENUMS.items():
        if r.get(k) not in allowed:
            out.append(f"{k}={r.get(k)!r}")
    for k in LISTS:
        if not isinstance(r.get(k), list):
            out.append(f"{k} not a list")
    for k in BOOLS:
        if not isinstance(r.get(k), bool):
            out.append(f"{k} not bool")
    if not isinstance(r.get("minor_issue_count"), int):
        out.append("minor_issue_count not int")
    if not isinstance(r.get("base_models_in_system_role"), int):
        out.append("base_models_in_system_role not int")
    harness = r.get("harness", "")
    if not (harness in ("none", "unclear") or str(harness).startswith(("custom", "off-the-shelf"))):
        out.append(f"harness={harness!r}")
    for m in r.get("models") or []:
        if not isinstance(m, dict) or m.get("role") not in ROLES or not isinstance(m.get("dated_snapshot"), bool):
            out.append(f"bad model entry {m!r}")
            break
    return out


def main():
    cmd, args = sys.argv[1], sys.argv[2:]
    done_ids = set(launched())
    if cmd == "next":
        n = int(args[0])
        todo = [i for i in IDS if i not in done_ids and not (OUT / f"{i}.md").exists()]
        print(" ".join(todo[:n]))
    elif cmd == "mark":
        with LOG.open("a") as f:
            for i in args:
                assert i in IDS, i
                f.write(json.dumps({"id": i, "at": datetime.now(timezone.utc).isoformat()}) + "\n")
    elif cmd == "status":
        lau = launched()
        valid = [i for i in IDS if not problems(i)]
        written = [i for i in IDS if (OUT / f"{i}.md").exists()]
        invalid = {i: problems(i) for i in written if problems(i)}
        inflight = [i for i in dict.fromkeys(lau) if not (OUT / f"{i}.md").exists()]
        print(f"frame {len(IDS)} | launched {len(set(lau))} | written {len(written)} "
              f"| valid {len(valid)} | in flight {len(inflight)} | remaining {len(IDS) - len(set(lau))}")
        if inflight:
            print("in flight:", " ".join(inflight))
        for i, p in invalid.items():
            print("INVALID", i, "; ".join(p))
    elif cmd == "check":
        for i in args:
            print(i, problems(i) or "ok")


if __name__ == "__main__":
    main()
