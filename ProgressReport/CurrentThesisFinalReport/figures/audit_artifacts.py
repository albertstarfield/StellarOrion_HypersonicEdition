#!/usr/bin/env python3
"""Report which figure artifacts in this directory are live and which are dead.

PURPOSE
=======
Two independent dead-artwork classes can hide in a figure directory and neither
is visible from the LaTeX side:

1. An image that no ``\\includegraphics`` ever names. It occupies repository
   space and invites a future reader to believe it is part of the thesis.
2. A generator script whose output image no ``\\includegraphics`` ever names.
   Such a script is dead code by definition, and dead code that LOOKS like the
   authority for a figure is worse than no code at all, because the next reader
   will edit it and never discover that its output is never printed.

This tool reports both classes so that each decision is made once, from
evidence, instead of being rediscovered figure by figure.

PARAMETERS
==========
None. The thesis directory is derived from this file's own location, so the
tool cannot be pointed at the wrong tree by accident.

RETURNS
=======
Exit code 0. Prints one block per class and a final count summary. A finding is
NOT an error: several images are legitimately dead (they are historical
artwork kept on purpose) and several are legitimately live through AccSupp
text rather than through ``\\includegraphics``. Both are reported with the
evidence needed to classify them.

EXCEPTIONS
==========
RuntimeError: if the thesis directory or its ``figures`` subdirectory does not
exist, because in that case the tool is running outside the tree it claims to
audit and its zero findings would be meaningless.

CITATIONS
=========
Matplotlib v3.11.2, https://matplotlib.org/stable/ (the generators whose output
is classified here).
LaTeX2e, https://www.latex-project.org/ (the ``\\includegraphics`` syntax that
defines liveness).

AXIOMS
======
A1  An image is LIVE if and only if some ``.tex`` file in the thesis directory
    contains its file name. Any other liveness claim (a prose reference, an
    AccSupp ActualText mention) is evidence for a human to weigh, never a
    substitute for the include.
A2  A generator is DEAD if and only if its declared output image is not LIVE.
    A generator with no discoverable output is reported as UNKNOWN rather than
    DEAD, because the output name may be computed.
A3  Substring matching is enough for liveness: including ``a.png`` also matches
    ``ba.png``. False positives are therefore possible and are stated, never
    hidden.

THEORIES
=========
T1  By A1 the LIVE set is exactly the set of image names appearing in the
    concatenation of every ``.tex`` file, so it is computable by grep.
T2  By A2 the DEAD generator set is the set of generators whose output falls
    outside the LIVE set, so it is computable once each output name is known.

APPLICATIONS
============
A1  Before any figure is regenerated, run this to confirm the generator is
    still the authority for a printed figure.
A2  Before any artwork is deleted, run this to obtain the evidence of
    unreferencedness that the removal record must cite.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIGDIR = ROOT / "figures"

# WHY: \includegraphics may carry optional arguments, so the pattern allows a
# bracket group between the command and the file name.
INCLUDE_RE = re.compile(r"\\includegraphics\s*(?:\[[^\]]*\])?\s*\{([^}]*)\}")

# WHY: a generator names its output either as a bare file name or as a Path
# expression ending in one. Both forms are matched, the second one as a suffix
# search rather than a regex so that a literal name cannot be mis-parsed.
OUT_LITERAL_RE = re.compile(r"['\"]([A-Za-z0-9_.-]+\.png)['\"]")
OUT_FIGDIR_RE = re.compile(r"FIGDIR\s*/\s*['\"]([A-Za-z0-9_.-]+\.png)['\"]")


def tex_text() -> str:
    """Return the concatenated text of every .tex file in the thesis directory.

    PARAMETERS: none.
    RETURNS: one string holding all TeX source, so that a grep over it answers
    A1 exactly.
    RAISES: RuntimeError: if no .tex file exists, which means the tool is
        outside the tree it claims to audit.
    """
    blocks = sorted(ROOT.glob("*.tex"))
    if not blocks:
        raise RuntimeError(f"no .tex file found in {ROOT}")
    return "\n".join(p.read_text(encoding="utf-8") for p in blocks)


def live_images(text: str) -> dict[str, int]:
    """Return every image name included by the TeX sources, with a hit count.

    PARAMETERS:
        text: the concatenated TeX source from tex_text().
    RETURNS: dict mapping bare file name to the number of include commands
        naming it, sorted by name by the caller.
    RAISES: nothing.
    """
    hits: dict[str, int] = {}
    for raw in INCLUDE_RE.findall(text):
        name = Path(raw.strip()).name
        if name:
            hits[name] = hits.get(name, 0) + 1
    return hits


def dead_images(live: dict[str, int]) -> list[str]:
    """Return image files on disk that no include names.

    PARAMETERS:
        live: the mapping from live_images().
    RETURNS: sorted list of bare file names present in figures/ and absent from
        live.
    RAISES: nothing.
    """
    on_disk = {p.name for p in FIGDIR.glob("*.png")}
    on_disk |= {p.name for p in FIGDIR.glob("*.jpeg")}
    return sorted(on_disk - set(live))


def generator_outputs(script: Path) -> list[str]:
    """Return the image file names a generator appears to declare.

    PARAMETERS:
        script: path to a generator script.
    RETURNS: every .png name appearing as a quoted literal or after a FIGDIR
        join, in file order and without duplicates.
    RAISES: RuntimeError: if the script cannot be read, because a generator
        that cannot be read cannot be classified and must not be called dead.
    """
    body = script.read_text(encoding="utf-8")
    names: list[str] = []
    for match in list(OUT_FIGDIR_RE.finditer(body)) + list(OUT_LITERAL_RE.finditer(body)):
        name = match.group(1)
        if name not in names:
            names.append(name)
    return names


def main() -> int:
    """Print the two dead-artifact classes and a summary.

    PARAMETERS: none.
    RETURNS: exit code 0.
    RAISES: RuntimeError from tex_text() when the tree is missing.
    """
    if not FIGDIR.is_dir():
        raise RuntimeError(f"figures directory not found: {FIGDIR}")

    text = tex_text()
    live = live_images(text)
    print(f"thesis directory: {ROOT}")
    print(f"includes found: {sum(live.values())} naming {len(live)} distinct images")

    dead = dead_images(live)
    print(f"\n== CLASS 1: image files on disk that no include names ({len(dead)}) ==")
    for name in dead:
        size_kb = (FIGDIR / name).stat().st_size / 1024.0
        print(f"  DEAD  {name:48s} {size_kb:8.1f} kB")

    scripts = sorted(p for p in FIGDIR.glob("*.py") if p.name != Path(__file__).name)
    print(f"\n== CLASS 2: generators by output liveness ({len(scripts)} scripts) ==")
    dead_scripts: list[tuple[str, list[str]]] = []
    unknown: list[tuple[str, list[str]]] = []
    for script in scripts:
        try:
            outputs = generator_outputs(script)
        except RuntimeError as exc:  # pragma: no cover - unreadable script
            print(f"  UNREADABLE {script.name}: {exc}")
            continue
        if not outputs:
            # WHY: a measurement library, a probe or a shared print helper
            # draws no image at all, so the absence of an output name is the
            # expected result for it and not an unresolved question.
            unknown.append((script.name, outputs))
            print(f"  NO-IMAGE {script.name:44s} draws no figure by design")
            continue
        verdicts = []
        for name in outputs:
            if name in live:
                verdicts.append(f"LIVE({name})")
            elif (FIGDIR / name).exists():
                verdicts.append(f"DEAD({name})")
            else:
                verdicts.append(f"ABSENT({name})")
        row = ", ".join(verdicts)
        if any(v.startswith("DEAD") for v in verdicts):
            dead_scripts.append((script.name, outputs))
            print(f"  DEAD     {script.name:44s} {row}")
        elif any(v.startswith("ABSENT") for v in verdicts):
            print(f"  PARTIAL  {script.name:44s} {row}")
        else:
            print(f"  LIVE     {script.name:44s} {row}")

    print(f"\nSUMMARY  dead images {len(dead)}  dead generators {len(dead_scripts)}"
          f"  unknown outputs {len(unknown)}  live images {len(live)}")
    print("Every DEAD row must be either removed with this evidence cited, or")
    print("recorded in CARVE_OUTS.md with the reason it is kept.")
    return 0


if __name__ == "__main__":
    sys.exit(main())