# Recheck of the classification

## Blind recode of the title/abstract labels

The labels come from Claude Haiku 5.5. GPT-6.1 Sol agents recoded, from title
and abstract only and without access to the original labels
([prompt.txt](prompt.txt)), the 228 papers with a substantive or proposed role
of a language model and 21 random preprints of the reading queue outside that
frame ([sample.json](sample.json), seed 20261028). [compare.py](compare.py)
writes [agreement.json](agreement.json).

| Axis (the 228 papers) | κ | Raw agreement |
| --- | ---: | ---: |
| Scope | 0.86 | 90% |
| Primary use | 0.82 | 84% |
| Agent form | 0.80 | 84% |
| Breadth | 0.71 | 82% |
| Paper kind | 0.71 | 81% |
| Autonomy | 0.66 | 74% |

- Sol confirms the role of 227 of the 228 papers (κ = 0.76 for frame
  membership over all 249 recoded preprints).
- Of the 21 preprints outside the frame, Sol places 7 in it, 5 of them outside
  condensed matter, materials and quantum research: Haiku tends to code no role
  for language-model papers outside the domain.
- The most frequent scope disagreement is adjacent quantum research (Haiku)
  against condensed matter (Sol).

## LLM-free topic check

[lexical.py](lexical.py) fits TF-IDF + NMF to the titles and abstracts of the
228 papers ([lexical.json](lexical.json)). With eight topics (restart ARI
median 0.85, minimum 0.53) the clusters follow what the AI does (computational
workflows, synthesis and literature-driven discovery, vision-language models and
microscopy, optimization and design, property prediction and generative design,
proofs, quantum software, formalization in Lean) rather than the physical system
it is applied to.
