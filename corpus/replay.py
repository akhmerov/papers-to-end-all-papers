"""Replay the registered searches directly against the arXiv API.

    python3 -I corpus/replay.py [--only QUERY_ID ...] [--out DIR]

The original acquisition used a private harvesting tool with a local cache.
This script needs only the Python standard library. It runs each registered
query (queries/arxiv.json) with arXiv's own pagination, writes the normalised
records to DIR/<query-id>.jsonl, and compares the identifiers with the frozen
snapshot (arxiv.json) and the totals recorded at acquisition
(queries/arxiv-ledger.csv).

A replay will not match the snapshot exactly: arXiv adds, withdraws and
re-indexes records.

Environment: CONTACT_EMAIL (sent to arXiv as a courtesy, optional).
"""

import argparse
import csv
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ATOM = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom",
        "os": "http://a9.com/-/spec/opensearch/1.1/"}
ARXIV_PAGE = 500
ARXIV_DELAY = 3.5  # seconds between requests, as the arXiv API terms ask


def agent():
    email = os.environ.get("CONTACT_EMAIL")
    return "papers-to-end-all-papers-replay/0.1" + (f" (mailto:{email})" if email else "")


class FetchError(RuntimeError):
    """HTTP failure, reported with the host only."""


def fetch(url, attempts=6):
    try:
        return _fetch(url, attempts)
    except urllib.error.HTTPError as error:
        raise FetchError(f"HTTP {error.code} from {urllib.parse.urlsplit(url).netloc}") from None
    except urllib.error.URLError as error:
        raise FetchError(f"{error.reason} from {urllib.parse.urlsplit(url).netloc}") from None


def _fetch(url, attempts):
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": agent()}), timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == attempts - 1:
                raise
            wait = int(error.headers.get("Retry-After") or 0) or 30 * 2 ** attempt
        except urllib.error.URLError:
            if attempt == attempts - 1:
                raise
            wait = 30 * 2 ** attempt
        print(f"  retry in {wait} s", flush=True)
        time.sleep(wait)


def arxiv_records(spec):
    start, total = 0, None
    while total is None or start < min(total, spec.get("max_results", total)):
        params = {"search_query": spec["query"], "start": start, "max_results": ARXIV_PAGE,
                  "sortBy": {"submitted_date": "submittedDate"}.get(spec.get("sort_by"), "submittedDate"),
                  "sortOrder": spec.get("sort_order", "descending")}
        root = ET.fromstring(fetch("https://export.arxiv.org/api/query?" + urllib.parse.urlencode(params)))
        total = int(root.findtext("os:totalResults", "0", ATOM))
        entries = root.findall("a:entry", ATOM)
        for e in entries:
            yield {
                "arxiv_id": re.sub(r"v\d+$", "", e.findtext("a:id", "", ATOM).rsplit("/abs/", 1)[-1]),
                "title": " ".join(e.findtext("a:title", "", ATOM).split()),
                "abstract": " ".join(e.findtext("a:summary", "", ATOM).split()),
                "authors": [a.findtext("a:name", "", ATOM) for a in e.findall("a:author", ATOM)],
                "submitted": e.findtext("a:published", "", ATOM),
                "updated": e.findtext("a:updated", "", ATOM),
                "categories": [c.get("term") for c in e.findall("a:category", ATOM)],
                "doi": e.findtext("arxiv:doi", None, ATOM),
            }
        if not entries:
            break
        start += len(entries)
        time.sleep(ARXIV_DELAY)


def ledger_totals():
    with (HERE / "queries" / "arxiv-ledger.csv").open() as f:
        return {r["query_id"]: r["provider_total_results"] for r in csv.DictReader(f)}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", nargs="+")
    parser.add_argument("--out", type=Path, default=HERE / "replay")
    args = parser.parse_args()
    snapshot = {r["arxiv_id"] for r in json.loads((HERE / "arxiv.json").read_text())}
    report = []
    totals = ledger_totals()
    for query in json.loads((HERE / "queries" / "arxiv.json").read_text()):
        if args.only and query["id"] not in args.only:
            continue
        print(query["id"], flush=True)
        started = datetime.now(timezone.utc).isoformat()
        records = list(arxiv_records(query["spec"]))
        path = args.out / f"{query['id']}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records))
        ids = {r["arxiv_id"] for r in records}
        row = {"query_id": query["id"], "started_at": started, "records": len(records),
               "total_at_acquisition": totals.get(query["id"]),
               "in_snapshot": len(ids & snapshot), "not_in_snapshot": len(ids - snapshot)}
        report.append(row)
        print("  " + json.dumps(row), flush=True)
    (args.out / "report.json").write_text(json.dumps(report, indent=1) + "\n")


if __name__ == "__main__":
    main()
