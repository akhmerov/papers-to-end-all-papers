"""Update the file digests in validation.json after a published file in this directory changes.

    pixi run rehash

tools/check_public.py fails while any digest is stale.
"""

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def digests():
    v = json.loads((HERE / "validation.json").read_text())
    return v, {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest() for name in v["files"]}


def main():
    v, current = digests()
    changed = [n for n in current if current[n] != v["files"][n]]
    v["files"] = current
    (HERE / "validation.json").write_text(json.dumps(v, indent=2, ensure_ascii=False) + "\n")
    print("updated:", ", ".join(changed) or "nothing")


if __name__ == "__main__":
    main()
