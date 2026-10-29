"""Run one prompt template over many jobs with a command-line coding agent.

    python3 -I agents/run_agents.py PROMPT JOBS [--workers N] [--dry-run]

PROMPT is a template from this repository (for example review/prompts/review-v2.txt).
JOBS is a JSON-lines file; each line maps placeholder names to values, for
example {"ID": "2605.00803", "OUT": "/path/to/work/reviews-v2/2605.00803.md"}.
{REPO} defaults to this repository and {WORK} to $REVIEW_WORK or review/work.
A job is skipped when its OUT file already exists and is not empty.

The agent command is taken from AGENT_COMMAND and receives the prompt on
standard input. Examples:

    AGENT_COMMAND='codex exec --model gpt-6.1-sol -'
    AGENT_COMMAND='claude --print --model claude-opus-5-5'

The study ran these prompts through an agent orchestrator, one independent
agent per job; any harness that gives the agent web access and file write
access inside the working directory is equivalent. Each run is logged to
{WORK}/agent-runs.jsonl.
"""

import argparse
import json
import os
import re
import shlex
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def render(template, values):
    """Fill {NAME} placeholders; {{ and }} are literal braces (str.format style)."""
    def sub(match):
        name = match.group(1)
        if name not in values:
            raise KeyError(f"placeholder {{{name}}} has no value")
        return str(values[name])
    text = re.sub(r"(?<!\{)\{([A-Z_]+)\}(?!\})", sub, template)
    return text.replace("{{", "{").replace("}}", "}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("prompt", type=Path)
    parser.add_argument("jobs", type=Path)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=3600, help="seconds per job")
    parser.add_argument("--dry-run", action="store_true", help="print the first rendered prompt and the plan")
    args = parser.parse_args()

    work = Path(os.environ.get("REVIEW_WORK", REPO / "review" / "work")).resolve()
    defaults = {"REPO": REPO, "WORK": work}
    template = args.prompt.read_text()
    jobs = [{**defaults, **json.loads(line)} for line in args.jobs.read_text().splitlines() if line.strip()]
    pending = [j for j in jobs if not (j.get("OUT") and Path(j["OUT"]).exists() and Path(j["OUT"]).stat().st_size)]
    prompts = [render(template, j) for j in pending]
    print(f"{len(jobs)} jobs, {len(pending)} to run", flush=True)
    if args.dry_run:
        if prompts:
            print(prompts[0])
        return
    command = shlex.split(os.environ["AGENT_COMMAND"])
    work.mkdir(parents=True, exist_ok=True)
    log = work / "agent-runs.jsonl"

    def run(job, prompt):
        started = datetime.now(timezone.utc).isoformat()
        try:
            result = subprocess.run(command, input=prompt, text=True, capture_output=True, timeout=args.timeout,
                                    cwd=work)
            code = result.returncode
        except subprocess.TimeoutExpired:
            code = 124
        entry = {"prompt": str(args.prompt), "job": {k: str(v) for k, v in job.items() if k not in defaults},
                 "command": command, "started_at": started,
                 "ended_at": datetime.now(timezone.utc).isoformat(), "exit_code": code}
        with log.open("a") as f:
            f.write(json.dumps(entry) + "\n")
        print(f"exit {code}: {entry['job']}", flush=True)

    with ThreadPoolExecutor(args.workers) as pool:
        list(pool.map(run, pending, prompts))


if __name__ == "__main__":
    main()
