"""Draw a seeded random sample of arXiv records for independent full-text review."""

import csv
import os
import json
import random
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
# Working directory of the review run (reviews, records and intermediate files);
# set REVIEW_WORK to point elsewhere. Its contents are not published.
HERE = Path(os.environ.get("REVIEW_WORK", REPO / "review" / "work")).resolve()
SOURCE = REPO / "classification" / "classified.csv"
SEED = 20261025
SIZE = 20
MAIN_SCOPES = {"condensed-matter", "materials-science"}
KINDS = {"application", "method", "benchmark"}


def in_frame(row):
    scopes = {row["scope"], *json.loads(row["application_scopes"] or "[]")}
    return (
        row["provider"] == "arxiv"
        and row["llm_role"] == "substantive"
        and row["kind"] in KINDS
        and bool(scopes & MAIN_SCOPES)
    )


rows = sorted(
    (r for r in csv.DictReader(SOURCE.open()) if in_frame(r)),
    key=lambda r: r["native_id"],
)
sample = random.Random(SEED).sample(rows, SIZE)
out = {
    "seed": SEED,
    "frame": "arXiv; llm_role=substantive; kind in application/method/benchmark; "
    "scope or application_scopes in condensed-matter/materials-science",
    "frame_size": len(rows),
    "sample": [
        {"native_id": r["native_id"], "title": r["title"], "url": r["url"]}
        for r in sample
    ],
}
(HERE / "sample.json").write_text(json.dumps(out, indent=2) + "\n")
print(len(rows))
for r in sample:
    print(r["native_id"], r["title"][:100])
