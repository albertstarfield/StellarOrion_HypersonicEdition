#!/usr/bin/env python3
"""Normalise British spellings to the document's US convention.

The thesis convention is US spelling (audit.py dim39, whose docstring records
that all 42 British forms were previously converted). Round-1 prose editors
introduced British forms back into touched text, producing 5 mixed pairs that
dim39 flags. This tool converts every British form of the nine audited word
families in all *.tex files, case-preserving initial capitals.

ref.bib is deliberately excluded: its fields hold published titles that must
never be altered.

Usage (workdir = thesis dir): python3 fix_uk_to_us.py          # dry run
                              python3 fix_uk_to_us.py ==apply  # edit files
Exit code 0 = success.
"""
import re
import sys
from pathlib import Path

# British -> American replacements for the nine audited families.
# Longest stems first so "centred" is consumed before "centre".
PAIRS = [
    ("initialisations", "initializations"),
    ("initialises", "initializes"),
    ("initialise", "initialize"),
    ("characterisation", "characterization"),
    ("characterises", "characterizes"),
    ("characterise", "characterize"),
    ("dimensionalised", "dimensionalized"),
    ("normalisation", "normalization"),
    ("maximisation", "maximization"),
    ("maximiser", "maximizer"),
    ("maximise", "maximize"),
    ("minimises", "minimizes"),
    ("minimised", "minimized"),
    ("minimising", "minimizing"),
    ("minimise", "minimize"),
    ("summarises", "summarizes"),
    ("summarised", "summarized"),
    ("summarise", "summarize"),
    ("optimising", "optimizing"),
    ("normalises", "normalizes"),
    ("normalised", "normalized"),
    ("normalise", "normalize"),
    ("modelling", "modeling"),
    ("optimisation", "optimization"),
    ("optimisations", "optimizations"),
    ("optimiser", "optimizer"),
    ("optimised", "optimized"),
    ("optimise", "optimize"),
    ("behaviours", "behaviors"),
    ("behaviour", "behavior"),
    ("analysed", "analyzed"),
    ("analyse", "analyze"),
    ("centred", "centered"),
    ("centres", "centers"),
    ("centre", "center"),
    ("colours", "colors"),
    ("colour", "color"),
    ("fibres", "fibers"),
    ("fibre", "fiber"),
    ("utilised", "utilized"),
    ("utilise", "utilize"),
]


def convert(text: str) -> tuple:
    """Return (converted_text, change_count) for one file's content."""
    n = 0
    for brit, amer in PAIRS:
        # word-boundary aware, both lower and capitalised spellings
        for b, a in ((brit, amer), (brit.capitalize(), amer.capitalize())):
            pattern = re.compile(r"\b" + re.escape(b) + r"\b")
            hits = pattern.findall(text)
            if hits:
                text = pattern.sub(a, text)
                n += len(hits)
    return text, n


def main() -> int:
    """Dry-run by default; ==apply rewrites files in place."""
    apply = "--apply" in sys.argv
    total = 0
    for path in sorted(Path(".").glob("*.tex")):
        original = path.read_text(encoding="utf-8")
        converted, n = convert(original)
        if n:
            total += n
            print(f"{'APPLIED' if apply else 'DRY'} {path.name}: {n} forms")
            if apply:
                path.write_text(converted, encoding="utf-8")
    print(f"total: {total}{' (files written)' if apply else ' (dry run, use --apply)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
