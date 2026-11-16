#!/usr/bin/env bash
# Thesis build driver: pdflatex + bibtex + pdflatex x2, then warning report.
# Usage: ./build_thesis.sh [--clean] [--outdir DIR]
# Citation: TeX Live 2026 latexmk/pdflatex - https://tug.org/texlive/
set -uo pipefail

THESIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$THESIS_DIR" || { echo "FATAL: cannot cd to $THESIS_DIR"; exit 1; }

CLEAN=0
[[ "${1:-}" == "--clean" ]] && CLEAN=1

export PATH="/Library/TeX/texbin:$PATH"

for bin in pdflatex bibtex; do
  command -v "$bin" >/dev/null 2>&1 || { echo "FATAL: $bin not found on PATH"; exit 1; }
done
echo "pdflatex: $(command -v pdflatex)"
echo "bibtex : $(command -v bibtex)"

if [[ $CLEAN -eq 1 ]]; then
  echo "=== CLEAN ==="
  rm -f main.aux main.log main.bbl main.blg main.brf main.lof main.lot main.out main.toc
  rm -f *.aux
fi

echo "=== PASS 1: pdflatex ==="
pdflatex -interaction=nonstopmode -file-line-error main.tex > /tmp/thesis_p1.out 2>&1
echo "exit=$?"

echo "=== PASS 2: bibtex ==="
bibtex main > /tmp/thesis_bib.out 2>&1
echo "exit=$?"

echo "=== PASS 3: pdflatex ==="
pdflatex -interaction=nonstopmode -file-line-error main.tex > /tmp/thesis_p3.out 2>&1
echo "exit=$?"

# Convergence loop, replacing the old fixed PASS 4.
#
# WHY: with a fixed pass count a from-scratch build (aux, bbl, toc, lof, lot, brf
# all deleted) ends on a log that still carries TeX's own rerun requests,
#     "Label(s) may have changed. Rerun to get cross-references right."
#     "File `main.brf' has changed."
# and report_warnings.py counts them as warnings. Measured: four passes left 2
# such warnings, a fifth pass cleared them and the verdict became CLEAN. Rather
# than hard-code a fifth pass, keep going until the log stops asking to be rerun,
# with a bounded number of attempts so a genuinely oscillating document cannot
# loop forever.
echo "=== PASSES 4+: pdflatex until the log stops requesting a rerun ==="
MAX_PASSES=8
for pass in 4 5 6 7 8 9 10 11; do
  pdflatex -interaction=nonstopmode -file-line-error main.tex > "/tmp/thesis_p${pass}.out" 2>&1
  rc=$?
  hard=$(grep -c "^!" main.log || true)
  echo "  pass ${pass}: exit=${rc}, hard errors=${hard}"
  # Success is decided from the LOG, not from pdflatex's exit status.
  #
  # MEASURED: this document makes pdflatex exit 1 while main.log contains zero
  # "!" error lines. An earlier version of this driver treated a non-zero exit as
  # fatal and stopped at pass 4, leaving two rerun warnings in the report. Exit
  # status alone is therefore not a usable success signal here; the log is.
  if [[ "$hard" -gt 0 ]]; then
    echo "  pdflatex reported ${hard} hard error(s) on pass ${pass}; stopping"
    break
  fi
  if ! grep -qE "Rerun to get|Label\(s\) may have changed|has changed\.|may have changed\." main.log; then
    echo "  converged after pass ${pass}: main.log requests no rerun and has no errors"
    break
  fi
  if [[ $pass -eq $MAX_PASSES ]]; then
    echo "  WARNING: still requesting a rerun after ${MAX_PASSES} passes"
  fi
done

echo
echo "########## WARNING / ERROR REPORT ##########"
python3 report_warnings.py
