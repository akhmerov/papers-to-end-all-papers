"""Normalise the model names extracted by the reviewers.

Each extracted model becomes a canonical key such as "gpt-5.4-mini",
"claude-opus-4.6" or "qwen3-8b". Generic or unnamed entries ("LLM", "GPT",
"one local language model") map to None. Run directly to write model_keys.json,
the list of canonical keys and how often each occurs, which is the input for
the release-date lookup.
"""

import collections
import os
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
# Working directory of the review run (reviews, records and intermediate files);
# set REVIEW_WORK to point elsewhere. Its contents are not published.
HERE = Path(os.environ.get("REVIEW_WORK", REPO / "review" / "work")).resolve()

# Models the reviewers left out because the paper names them only in an
# AI-use statement, while the statement describes scientific use (proof
# discovery or formalization). Filled in from the review texts and the papers.
OVERRIDES = {
    "2607.26305": ["GPT-5.5 Pro", "GPT-5.5"],
    "2609.25000": ["ChatGPT 6"],
    "2609.34119": ["GPT-6 Astra Pro"],
}

ROLES = ("system", "baseline", "judge", "data-generation", "other")

GENERIC = re.compile(
    r"^(llm|gpt|gemini|claude|claude opus|mistral|llama3?|qwen3?|gpt-based|chatgpt|"
    r"unnamed.*|one local.*|fourth model.*|other models.*|q&a-llm|deepseek-pro)$")


def canonical(name, version=None):
    s = (name or "").strip().lower()
    v = (version or "").strip().lower()
    # Prefer an informative version string when the name itself is bare.
    if re.fullmatch(r"[\d.]+|4o", s) and v:
        s = v
    s = re.sub(r"\[1m\]", "", s)
    s = re.sub(r"\(([^)]*)\)", lambda m: " " + m.group(1) if re.search(r"gpt-5\.6 sol|\d+b", m.group(1)) else "", s)
    s = s.split(" / ")[0]
    s = re.sub(r"^(openai|anthropic|google|meta-llama|qwen|deepseek-ai|deepseek|x-ai|mistralai|moonshotai|zai-org)/", "", s)
    s = s.replace("chaptgpt", "chatgpt").replace("chatgpt", "gpt").replace("gpt5", "gpt-5").replace("gpt4", "gpt-4")
    s = re.sub(r"\b(google|openai|meta)\s+", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-(reasoning|thinking|no-thinking|extended-thinking|extended|instruct|it|turbo|preview|latest|api|"
               r"default|no-reasoning|extended-reasoning|codex-cli|maas|fp8|awq|ollama|q4_0)\b", "", s)
    s = s.replace(":", "-")
    # Bare numbers that belong to OpenAI ("4o", "5.2", "5.4-nano", "o3").
    if re.fullmatch(r"(4o|[45](\.\d)?(-\w+)?)", s):
        s = "gpt-" + s
    # Claude: unify "opus 4.6", "claude-opus-4-6", "opus-4.6".
    s = re.sub(r"^(opus|sonnet|haiku|fable|mythos)", r"claude-\1", s)
    s = re.sub(r"^claude-(\d)", r"claude-sonnet-\1", s) if s.startswith("claude-3.") else s
    m = re.match(r"^claude-(opus|sonnet|haiku|fable|mythos)-?(\d)(?:[.-](\d))?(?:-\d{8})?$", s)
    if m:
        s = f"claude-{m.group(1)}-{m.group(2)}" + (f".{m.group(3)}" if m.group(3) else "")
    s = re.sub(r"^claude-sonnet-3\.7$", "claude-sonnet-3.7", s)
    m = re.match(r"^claude-haiku-?3\.5$", s)
    if m:
        s = "claude-haiku-3.5"
    # OpenAI: strip dated snapshot suffixes but keep the base name.
    s = re.sub(r"^(gpt-[\w.-]+?|o\d(?:-mini)?|o3-deep-research)-20\d\d-\d\d-\d\d$", r"\1", s)
    s = re.sub(r"^gpt-o3-mini$", "o3-mini", s)
    s = re.sub(r"^gpt-5o-mini$", "gpt-5-mini", s)
    s = re.sub(r"^gpt-4\.0$", "gpt-4", s)
    s = re.sub(r"^openai-oss-120b$", "gpt-oss-120b", s)
    s = re.sub(r"^gpt-oss$", "gpt-oss-120b", s) if v.endswith("120b") else s
    s = re.sub(r"^gpt-5\.(\d)-?\(?codex\)?$", r"gpt-5.\1-codex", s)
    s = re.sub(r"^gpt-5-chat$|^gpt-5-thinking-.*$", "gpt-5", s)
    s = re.sub(r"^gpt-5\.2-extended-thinking$|^gpt-5\.2-extended$", "gpt-5.2", s)
    s = re.sub(r"-pro-?(reasoning)?$", "-pro", s)
    # Gemini: "gemini-3.1-pro", "gemini-2.5-flash".
    s = re.sub(r"^gemini-?(\d(?:\.\d)?)-?", r"gemini-\1-", s).rstrip("-")
    s = re.sub(r"^gemini-3\.0-", "gemini-3-", s)
    # DeepSeek, Qwen, Kimi and others.
    s = re.sub(r"^deepseek-v(\d(?:\.\d)?)-?", r"deepseek-v\1-", s).rstrip("-")
    s = re.sub(r"^deepseek-v4-(flash|pro).*", r"deepseek-v4-\1", s)
    s = re.sub(r"^deepseek-model-v3-together$|^deepseek-chat(-v3\.1)?$", lambda m: "deepseek-v3.1" if m.group(1) else "deepseek-v3", s)
    s = re.sub(r"^deepseek-r1(-8b)?$", "deepseek-r1", s)
    s = re.sub(r"^qwen-?(\d(?:\.\d)?)", r"qwen\1", s)
    s = re.sub(r"^qwen(\d(?:\.\d)?)\+", r"qwen\1-plus", s)
    s = re.sub(r"^qwen3-instruct-(\S+)$", r"qwen3-\1", s)
    s = re.sub(r"^kimi-?k", "kimi-k", s)
    s = re.sub(r"^(gemma)-?(\d)", r"\1-\2", s)
    s = re.sub(r"^llama-?(\d)", r"llama-\1", s)
    s = re.sub(r"^meta-llama-", "llama-", s)
    s = re.sub(r"^llama4-", "llama-4-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    if not s or GENERIC.match(s.replace("-", " ")) or GENERIC.match(s):
        return None
    return s


def paper_models(rec, roles=ROLES):
    """Canonical keys of the models a paper actually ran, by role."""
    out = []
    for name, version, role in rec["all_models"]:
        if role in roles:
            key = canonical(name, version)
            if key:
                out.append((key, role))
    for name in OVERRIDES.get(rec["id"], []):
        out.append((canonical(name), "system"))
    return out


def main():
    recs = json.loads((HERE / "v2_records.json").read_text())
    counts = collections.Counter()
    raw = collections.defaultdict(set)
    for r in recs:
        for name, version, role in r["all_models"]:
            if role in ROLES:
                raw[canonical(name, version)].add(name)
        for key, _ in set(paper_models(r)):
            counts[key] += 1
    keys = [{"key": k, "papers": n, "raw_names": sorted(raw.get(k, []))} for k, n in counts.most_common()]
    (HERE / "model_keys.json").write_text(json.dumps(keys, indent=1, ensure_ascii=False) + "\n")
    print(len(keys), "keys;", "dropped as generic:", sorted(raw.get(None, [])))
    for k in keys:
        print(k["papers"], k["key"], "<-", "; ".join(k["raw_names"])[:90])


if __name__ == "__main__":
    main()
