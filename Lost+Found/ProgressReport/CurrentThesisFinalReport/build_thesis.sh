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

echo "=== PASS 4: pdflatex ==="
pdflatex -interaction=nonstopmode -file-line-error main.tex > /tmp/thesis_p4.out 2>&1
echo "exit=$?"

echo
echo "########## WARNING / ERROR REPORT ##########"
python3 report_warnings.py
