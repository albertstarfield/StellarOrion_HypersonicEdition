# Humanization report — CurrentThesisFinalReport

Generated 2026-11-09. Source: `Lost+Found/ProgressReport/CurrentThesisFinalReport`.
Output: this folder (`CurrentThesisFinalReport_Humanized`), chapters 1–5 rewritten
paragraph by paragraph, LaTeX untouched.

## What the pipeline does

1. `texseg extract` classifies every source line as structural (commands, math,
   tables, verbatim) or prose, masks LaTeX fragments inside prose into
   `ZXQ<n>` placeholders and emits one TSV row per paragraph.
2. `run_humanize.py` ships each paragraph to the local humanizer model and
   retries up to four times until the rewrite passes the fidelity gate.
3. `texseg splice` re-validates every rewrite in Ada, unmasks the placeholders
   and writes the resulting chapter. A paragraph that fails any check keeps its
   original text verbatim, so a bad rewrite cannot corrupt the thesis.

## Numbers (measured, not estimated)

| chapter | blocks | replaced | kept | `\cite` kept | caps lost | numerals lost |
|---|---|---|---|---|---|---|
| chapter_01_introduction | 39 | 15 | 24 | 8/8 | 0 | 0 |
| chapter_02_literature_review | 242 | 148 | 94 | 67/67 | 0 | 0 |
| chapter_03_methodology | 128 | 60 | 68 | 18/18 | 0 | 0 |
| chapter_04_gate | 20 | 5 | 15 | 0/0 | 0 | 0 |
| chapter_04_results | 56 | 22 | 34 | 26/26 | 0 | 0 |
| chapter_05_conclusion | 14 | 6 | 8 | 8/8 | 0 | 0 |
| **total** | **499** | **256** | **243** | **127/127** | **0** | **0** |

69 blocks were never sent to the model (display math, tables, command-only
lines). Of the 430 paraphraseable blocks, 256 (59.5 %) were rewritten; 14 of the
originally accepted rewrites were thrown back to the original text by the final
audit (7 prompt echoes, 3 lost all-caps tokens, 4 lost their negation).

Build: `pdflatex main.tex` twice → 206 pages, 0 errors, 0 overfull boxes,
0 undefined references, 0 unconsumed `ZXQ` tokens, brace counts balanced.

Independent checks against the original PDF:

| measure | original | humanized |
|---|---|---|
| extracted words | 56 873 | 56 675 (−0.35 %) |
| figure labels | 53 | 53 |
| table labels | 23 | 23 |
| bracketed citations in text | 207 | 207 |
| rewrites that look truncated | — | 0 |
| prompt-echo paragraphs | — | 0 |

Similarity of each accepted rewrite to its source (difflib ratio): median 0.683;
53 % of rewrites fall below 0.70 (substantially reworded), 10 % above 0.95
(light touch only). Rewriting is uneven because a 1-billion-parameter model
sometimes returns a near copy — those blocks are reported, not hidden.

## Fidelity gate (Ada, `texlogic.adb`)

A rewrite is accepted only if all of these hold:

- every `ZXQ<n>` placeholder occurs exactly once, in the original order;
- placeholders that touched each other in the source still touch (the model may
  not slide a word between `Figure~` and `\ref{...}`); an injected space next to
  a glued placeholder is removed deterministically;
- every pure-integer token of the source reappears, counted outside placeholder
  runs so `ZXQ4` cannot satisfy a stray `4`;
- no parenthesised acronym appears that the source never had;
- word-count ratio stays within 0.7–1.5.

The Python boundary applies the same rules plus two more: an acronym may be
replaced by its expansion only if `abbreviations.tex` says so, and a
parenthesised acronym must be introduced by its real definition. A final audit
pass re-reads every accepted verdict and rejects prompt echoes, lost all-caps
tokens and lost negations.

## Defects found and fixed while auditing

1. Temperature 0.25 made the model echo its input verbatim; 0.55–0.8 rewrites.
2. The model relocated `\item` into the middle of a sentence and broke the
   build; `\item` is now kept outside the mask and a bullet always opens its own
   paragraph.
3. The model split `Figure~\ref{...}` into `Figure ~ and \ref{...}`; adjacency
   checking plus glue repair removed the artefact.
4. Placeholder digits satisfied the numeral check, letting a rewrite drop
   “4.57 m”; the check is now placeholder-blind.
5. The prompt rule about `ZXQ` tokens made the model invent tokens in plain
   paragraphs; the rule is now sent only when the paragraph contains tokens.
6. The model sometimes answered the instruction instead of paraphrasing it
   (“The provided text contains LaTeX fragments: … Copy each verbatim”) and
   sometimes dropped a negation or an all-caps token (`O$_2$` → `$_2$`). Ten
   such paragraphs reached the first PDF; the final audit sent them back to the
   original wording.

## Reproduce

```bash
cd ~/.hermes/cache/scratch/humanize_20261108
bash driver.sh                      # extract → model → splice, logs to driver.log
cd texseg && gnatprove -P texseg.gpr --mode=all --level=4 -j0
```

## Sources

[1] A. Starfield, “chapter_01_introduction.tex” … “chapter_05_conclusion.tex,”
StellarOrion Hypersonic Edition, `Lost+Found/ProgressReport/CurrentThesisFinalReport`,
2026.
[2] A. Starfield, “abbreviations.tex,” ibid. — acronym/expansion table used by the
fidelity gate.
[3] `~/.hermes/cache/scratch/humanize_20261108/driver.log` — per-block verdicts and
splice counts.
[4] `~/.hermes/cache/scratch/humanize_20261108/out/*.res.tsv` — raw model verdicts,
including the rejection reason for every block that kept its original wording.
[5] `~/.hermes/cache/scratch/humanize_20261108/logs/pdf_D.log` — pdflatex
transcript of the delivered build.
[6] AdaCore, “How to run GNATprove,” SPARK 2014 User’s Guide.
https://docs.adacore.com/spark2014-docs/html/ug/en/source/how_to_run_gnatprove.html
