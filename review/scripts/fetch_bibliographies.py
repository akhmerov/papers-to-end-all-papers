"""Fetch the bibliography of every reviewed paper from its latest arXiv version.

Sources, in order: the arXiv HTML rendering (one entry per ltx_bibitem), the
.bbl file in the source archive, and the reference section of the PDF text.
Downloads are cached in the directory given as the first argument, which
should be a fresh directory outside the repository; the extracted text goes to
citations/bibliographies.jsonl. Requests are spaced by three seconds.

Usage: python3 -I fetch_bibliographies.py ../data/bib-cache
"""

import html
import io
import os
import json
import re
import subprocess
import sys
import tarfile
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
# Working directory of the review run (reviews, records and intermediate files);
# set REVIEW_WORK to point elsewhere. Its contents are not published.
HERE = Path(os.environ.get("REVIEW_WORK", REPO / "review" / "work")).resolve()
OUT = HERE / "citations" / "bibliographies.jsonl"
AGENT = "papers-to-end-all-papers/0.1" + (f" (mailto:{os.environ['CONTACT_EMAIL']})" if os.environ.get("CONTACT_EMAIL") else "")


def get(url, path):
    if path.exists():
        return path.read_bytes()
    time.sleep(3)
    req = urllib.request.Request(url, headers={"User-Agent": AGENT})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = r.read()
            final = r.geturl()
    except urllib.error.HTTPError as e:
        data, final = b"", f"HTTP {e.code}"
    path.write_bytes(data)
    path.with_suffix(path.suffix + ".url").write_text(final)
    return data


def clean(s):
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def from_html(data):
    t = data.decode("utf-8", "replace")
    parts = re.split(r'<li[^>]*class="[^"]*ltx_bibitem[^"]*"', t)[1:]
    items = []
    for p in parts:
        p = p.split("</li>")[0]
        links = " ".join(re.findall(r'href="([^"#][^"]*)"', p))
        items.append((clean(p) + " " + links).strip())
    version = re.search(r'arxiv\.org/abs/\d{4}\.\d{5}(v\d+)', t)
    return items, version.group(1) if version else None


def from_source(data):
    try:
        tar = tarfile.open(fileobj=io.BytesIO(data))
    except tarfile.TarError:
        return []
    items = []
    for m in tar.getmembers():
        if m.isfile() and m.name.endswith((".bbl", ".bib")) and m.size < 5_000_000:
            text = tar.extractfile(m).read().decode("utf-8", "replace")
            split = re.split(r"\\bibitem|\n@", text)
            items += [re.sub(r"\s+", " ", x).strip() for x in split[1:]]
    return items


def from_pdf(data, path):
    if not data.startswith(b"%PDF"):
        return []
    txt = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True).stdout
    m = list(re.finditer(r"\n\s*(References|REFERENCES|Bibliography|BIBLIOGRAPHY)\s*\n", txt))
    tail = txt[m[-1].end():] if m else txt[int(len(txt) * 0.6):]
    return [re.sub(r"-\n\s*", "", tail).replace("\n", " ")]


def main():
    cache = Path(sys.argv[1])
    cache.mkdir(exist_ok=True)
    ids = [r["native_id"] for r in json.loads((HERE / "full_frame.json").read_text())["records"]]
    OUT.parent.mkdir(exist_ok=True)
    done = {}
    if OUT.exists():
        for line in OUT.read_text().splitlines():
            rec = json.loads(line)
            done[rec["id"]] = rec
    with OUT.open("a") as out:
        for pid in ids:
            if pid in done:
                continue
            items, version = from_html(get(f"https://arxiv.org/html/{pid}", cache / f"{pid}.html"))
            source = "html"
            if len(items) < 3:
                items, source = from_source(get(f"https://arxiv.org/e-print/{pid}", cache / f"{pid}.src")), "source"
            if len(items) < 3:
                pdf = cache / f"{pid}.pdf"
                items, source = from_pdf(get(f"https://arxiv.org/pdf/{pid}", pdf), pdf), "pdf"
            rec = {"id": pid, "source": source if items else "none", "version": version, "n_items": len(items), "items": items}
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            out.flush()
            print(pid, rec["source"], rec["n_items"], flush=True)


if __name__ == "__main__":
    main()
