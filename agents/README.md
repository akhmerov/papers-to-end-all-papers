# Running the agents

Every judgement in this study was made by a language-model agent following a
prompt in this repository: the abstract classification (Claude Haiku 5.5,
[../classification/classify.py](../classification/classify.py)), its blind
recode (GPT-6.1 Sol), the field and question coding (GPT-6.1 Sol and Claude Opus 5.5),
the full-text referee reports, the model release dates and the issue taxonomy
(GPT-6.1 Sol), and the verification of examples (Claude Opus 5.5).

The study ran the prompts through an agent orchestrator that started one
independent agent per job, with web access and write access to the working
directory. [run_agents.py](run_agents.py) does the same with any command-line
agent:

```sh
export AGENT_COMMAND='codex exec --model gpt-6.1-sol -'      # or: claude --print --model claude-opus-5-5
export REVIEW_WORK=/path/to/private/work
python3 -I agents/run_agents.py review/prompts/review-v2.txt jobs.jsonl --workers 10 --dry-run
```

`jobs.jsonl` has one JSON object per job mapping the prompt's placeholders to
values, for example `{"ID": "2605.00803", "OUT": "/path/to/private/work/reviews-v2/2605.00803.md"}`.
`{REPO}` is this repository and `{WORK}` the working directory. Jobs whose
output already exists are skipped, so an interrupted run can be restarted.

| Prompt | Placeholders | Agents in the study |
| --- | --- | --- |
| `review/prompts/review-v2.txt` | ID, OUT | 228 + 20 drift, GPT-6.1 Sol |
| `review/prompts/example-verification.txt` | ID, TITLE, ISSUE, ISSUE_ID, SAFE | 17, Claude Opus 5.5 |
| `review/prompts/model-dates.txt` | IN, OUT, EXTRA, EXTRA_SCHEMA (frontier timeline request, empty for one of the three agents) | 3, GPT-6.1 Sol |
| `review/prompts/issue-taxonomy.txt` | none besides WORK | 1, GPT-6.1 Sol |
| `review/prompts/issue-coding.txt` | IN, OUT | 4 + 2 recodes, GPT-6.1 Sol; 2 Claude Opus 5.5 |
| `classification/recheck/prompt.txt` | IN, OUT | 9, GPT-6.1 Sol |
| `classification/subjects/prompt-code-field.txt`, `prompt-code-question.txt` | OUT | 1 GPT-6.1 Sol + 1 Claude Opus 5.5 each |

Running the agents again will not reproduce the published labels exactly:
models change and sampling is not deterministic. The test–retest and
cross-model checks in [../review/README.md](../review/README.md) and
[../classification/recheck/README.md](../classification/recheck/README.md)
measure how much this matters.
