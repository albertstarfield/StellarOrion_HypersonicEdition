# ProgressReport — Week datings (from document contents)

Dates below are read from inside the documents themselves (LaTeX `.log`
first-line compile timestamps, `.tex` headers, README/Revision_1.md dates,
and PowerPoint `docProps/core.xml` created/modified), NOT from filesystem
mtimes.

Project: StellarOrion — Aerothermodynamics Optimization of HIAD IRVE-3
Geometry using DSMC and Genetic Algorithm (ITB thesis, Wahyu Suryo Samudro).

## Weekly progress reports

| Week | Folder | In-document date | Source |
|---|---|---|---|
| Week 1 | `Week 1/` | Compiled 22 Apr 2026 (03:23) | `Presentation_Week1.log` line 1 |
| Week 2 | `Week 2/` | Compiled 30 Apr 2026 (05:17) | `Presentation_Week2.log` line 1 |
| Week 3 | `Week 3/` | Compiled 30 Apr 2026 (05:17) | `Presentation_Week3.log` line 1 |
| Week 4 | `Week 4/` | Compiled 14 May 2026 (19:25 / 20:07) | `Week4_Report.log`, `Week4_Presentation.log` |
| Week 5 | `Week 5/` | Compiled 11 Jun 2026 (09:13 / 13:58) | `Week5_Presentation.log`, `BoltzmannToDSMC_Presentation.log` |
| Week 6 | `Week 6/` | 11 Jun 2026 (BoltzmannToDSMC template log only; no week-specific log) | `BoltzmannToDSMC_Presentation.log` |
| Week 7 | `Week 7/` | 11 Jun 2026 (BoltzmannToDSMC template log only) | `BoltzmannToDSMC_Presentation.log` |
| Week 8 | `Week 8/` | 11 Jun 2026 (BoltzmannToDSMC template log only) | `BoltzmannToDSMC_Presentation.log` |
| Week 9 | `Week 9/` | 11 Jun 2026 (BoltzmannToDSMC template log only) | `BoltzmannToDSMC_Presentation.log` |
| Week 10 | `Week 10/` | 11 Jun 2026 (BoltzmannToDSMC template log only) | `BoltzmannToDSMC_Presentation.log` |
| Week 11 | `Week 11/` | `\date{\today}` (no fixed date; BoltzmannToDSMC log 11 Jun 2026) | `BoltzmannToDSMC_Presentation.tex` |
| Week 12 | `Week 12/` | pptx created 2026-08-26, modified 2026-09-08 | `ProgressReport.pptx` docProps/core.xml |
| Week 13 | `Week 13/` | pptx created 2026-08-26, modified 2026-09-24 | `ProgressReport.pptx` docProps/core.xml |
| Week 14 | `Week 14/` | pptx created 2026-08-26, modified 2026-10-01 | `ProgressReport.pptx` docProps/core.xml |
| Week 15 | — | **Skipped intentionally (no report produced)** | — |
| Week 16 | `Week 16 LaTeX/` | `main.tex`: "Progress Report, Week 16"; content references 2026-09-26 run and 2026-10-14 refresh | `main.tex` lines 2, 438, 470 |
| Week 17 (LaTeX) | `Week 17 LaTeX/` | `main.tex`: "Progress Report, Week 17"; owner directive 2026-10-21; content references 2026-10-19 | `main.tex` lines 2, 43, 152 |
| Week 17 (narrative, template-driven) | `Week 17 Narrative Template Driven gen experimental/` | README date: 2026-10-21 | `README.md` line 9 |
| Week 18 (narrative, driven) | `Week 18 Narrative Driven/` | README date: 2026-10-27; deck saved 27 Oct 2026 11:52 | `README.md` line 9; `Revision_1.md` |

## Supporting archives / folders

| Folder | In-document date | Source |
|---|---|---|
| `Initial/` | (no date found in contents) | — |
| `Iter2Latex/` | (no date found; Albert thesis template) | `Albert_thesis_template/README.txt` |
| `LBMZero2Hero/` | (no date found) | — |
| `CurrentThesisFinalReport/` | Latest git commit 2026-10-27 16:31 +0700; content references 2026-10-27 | `git log` |
| `paperRef/` | (reference PDFs; no project date) | — |
| `PapersTemplateFromThesis/` | (paper templates; no project date) | — |
| `ThesisTemplateITB/` | empty | — |

## Notes

- Weeks 6–10 share a single `BoltzmannToDSMC_Presentation.log` dated 11 Jun 2026; no
  week-specific presentation log exists for those weeks, so their "date" is the
  shared template compile date.
- Week 11 uses `\date{\today}` (no fixed date) in its `.tex`.
- Week 15 was intentionally skipped (no report produced).
- `Week5/` (no space) is a separate, smaller archive distinct from `Week 5/`.