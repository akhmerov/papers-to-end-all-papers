# What the papers are about: field and question

Each of the 228 papers ([papers.jsonl](papers.jsonl): identifier, title and arXiv
abstract) is coded on two axes from its title and abstract:

- **Field** ([codebook-field.json](codebook-field.json)): the research community
  whose expertise is needed to judge the physics or materials content, grouped
  into quantum computing and information, material classes, techniques that
  apply to any material, and fields outside condensed matter, materials and
  quantum research.
- **Question** ([codebook-question.json](codebook-question.json)): the main
  question the paper answers, grouped by whether it concerns the physical world
  or the AI and its workflow.

GPT-6.1 Sol agents built the codebooks from the abstracts of an earlier, broader
candidate set. One GPT-6.1 Sol and one Claude Opus 5.5 agent then coded each axis
independently ([prompt-code-field.txt](prompt-code-field.txt),
[prompt-code-question.txt](prompt-code-question.txt); outputs `coded-*.json`).
[analyze.py](analyze.py) (`pixi run agreement`) writes the agreement between the
coders and the shares with bootstrap intervals to [summary.json](summary.json):
κ = 0.90 for the field and 0.90 for the question, 0.94 for whether the question
concerns the physical world.
