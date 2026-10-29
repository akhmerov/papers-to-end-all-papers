"""Write the full review frame: every arXiv record with substantive or proposed LLM use."""

import csv
import os
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
# Working directory of the review run (reviews, records and intermediate files);
# set REVIEW_WORK to point elsewhere. Its contents are not published.
HERE = Path(os.environ.get("REVIEW_WORK", REPO / "review" / "work")).resolve()
SOURCE = REPO / "classification" / "classified.csv"

rows = sorted(
    (r for r in csv.DictReader(SOURCE.open())
     if r["provider"] == "arxiv" and r["llm_role"] in ("substantive", "proposed")),
    key=lambda r: r["native_id"],
)
out = {
    "frame": "arXiv; llm_role in substantive/proposed; any scope",
    "size": len(rows),
    "records": [
        {"native_id": r["native_id"], "title": r["title"], "date": r["date"],
         "scope": r["scope"], "kind": r["kind"]}
        for r in rows
    ],
}
(HERE / "full_frame.json").write_text(json.dumps(out, indent=1) + "\n")
print(len(rows), len({r["native_id"] for r in rows}))
