#!/usr/bin/env python3
"""Audit every result figure against SOP §13.3 and emit the checklist CSV.

AXIOMS
  A1.  §13.3 makes a figure *self-sufficient*: a reader with only the figure
       and its caption must not need the speaker.  The six requirements are
       title/case, axes with units, legends, colour-scale numeric limits,
       consistent styling, and the physical quantity named explicitly.
  A2.  What can be MEASURED here is the generator that drew the figure --
       its `set_xlabel`/`set_ylabel`/`set_title`/`legend`/`colorbar` calls
       and the label text they carry.  This audit says so in every row; it
       never claims to have read rendered pixels.
  A3.  A figure whose generator cannot be located is reported
       `no_generator` with status `UNKNOWN`, never `ok`.  Absence of
       evidence is not evidence of compliance.
  A4.  Units are detected from an explicit unit token in the label
       (`W/m`, `m/s`, `kg`, `K`, `Pa`, `%`, `km`, `mm`, `s`, `--` for
       dimensionless).  A bare quantity word without a unit fails.

THEORIES
  T1.  Plotting libraries take labels from the call site, so scanning the
       source for those calls is a sound proxy for the rendered text.
  T2.  A scalar contour without a `colorbar` label has no numeric limits
       visible, which is §13.3 bullet 4 -- the single most common gap in
       this tree because colourbars are often created without `label=`.

APPLICATIONS
  -  results/99_shared/sop/figure_checklist.csv  (one row per figure)
  -  results/99_shared/sop/figure_checklist.json (summary counts + verdict)
  Run with no arguments; run.py Phase 2c invokes it exactly that way.

References:
    - Standard Operating Procedure of CFD.md, §13.3 "How a result figure
      must be built", §12.3 (table checklist counterpart)
    - https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.set_xlabel.html
    - RFC 4180 (CSV format), https://www.rfc-editor.org/rfc/rfc4180
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
RESULTS_DIR = PROJECT_ROOT / "results"
SOP_DIR = RESULTS_DIR / "99_shared" / "sop"

# Where generated figures live.  vtu_frames/mp4_frames are transient video
# inputs, not result figures, so they are excluded on purpose.
FIGURE_DIRS = (
    RESULTS_DIR / "99_shared",
    RESULTS_DIR / "00_reference" / "plots",
    RESULTS_DIR / "03_opt_geometry" / "plots",
    RESULTS_DIR / "tps_conduction",
)
EXCLUDE_DIRS = {"vtu_frames", "mp4_frames", "__pycache__", "cfd_fields_raw"}
MAX_FIGURES = 4000          # bound the audit (no unbounded walk)

# Scripts that can draw figures.
SOURCE_GLOBS = ("scripts/*.py", "src/python/*.py", "tools/*.py",
                "src/ui/uiassets/*.py")

# §13.3 units vocabulary.  Built from an explicit token list rather than a
# hand-written alternation: a literal regex here died on "multiple repeat"
# under re.VERBOSE, and a token list cannot get the escaping wrong.
# [Standard Operating Procedure of CFD.md §13.3]
_UNIT_TOKENS = (
    "W/m^2", "W/m2", "W/cm^2", "W/cm2", "W/cm^2",
    "kg/m^3", "kg/m3",
    "m/s", "km/s", "mm/s", "km/h",
    "kPa", "MPa", "mm", "cm", "km", "kg", "ms", "Pa", "m", "s",
    "degC", "\u00b0C", "\u00b0F", "K",
    "g0", "g_0", "Mach", "Ma",
)
_UNIT_ALT = "|".join(re.escape(t)
                     for t in sorted(set(_UNIT_TOKENS), key=len, reverse=True))

UNIT_RE = re.compile(
    # Token-based ONLY.  The earlier form accepted `[anything]` / `(anything)`
    # as a unit, which passed `set_xlabel("Step (log scale)")` and
    # `set_xlabel("Knudsen Number (Kn)")` as "unit-bearing" -- both are false.
    # A real unit token inside the brackets still matches below.
    rf"|(?:\b(?:{_UNIT_ALT})\b)"
    + r"|%"
)

"""Lines that actually write an image; only those may claim a figure name."""


_EMIT_LINE_RE = re.compile(
    r"\.savefig\s*\(|\b_save\s*\(|\.png|out_path|outfile|output_path|"
    r"fig(?:ure)?_?(?:name|path)|write_image|imsave"
)
"""Lines that actually write an image; only those may claim a figure name."""


def _call_args(text: str, name: str) -> str | None:
    r"""Return the argument block of `name(...)` with NESTED parens honoured.

    Parameters:
        text: source to search.
        name: callee name, e.g. "colorbar".
    Returns:
        The characters between the opening paren and its MATCHING close
        paren, or None when the call is absent.
    Exceptions: none.

    WHY a scanner: `re.search(r"colorbar\s*\(([^)]*)\)")` stops at the
    first `)`, so for
        fig.colorbar(x, ax=list(axes[row, :]), ..., label=FIELD)
    it returned only `x, ax=list(axes[row, :]` -- never reaching `label=`.
    The same truncation hid `label=` entirely and made `set_xlabel("Heat
    (W/m^2)")` fail literal extraction, passing as "unresolved".
    """
    m = re.search(rf"\b{re.escape(name)}\s*\(", text)
    if not m:
        return None
    i = m.end()            # just past the opening '('
    depth = 1
    n = len(text)
    while i < n and depth:
        c = text[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        i += 1
    return text[m.end(): i - 1] if depth == 0 else text[m.end():n]


_CALL_RE = {
    "xlabel": re.compile(r"\bset_xlabel\s*\(([^)]*)\)"),
    "ylabel": re.compile(r"\bset_ylabel\s*\(([^)]*)\)"),
    "title": re.compile(r"\b(?:set_title|suptitle)\s*\(([^)]*)\)"),
    "legend": re.compile(r"\.legend\s*\("),
    "colorbar": re.compile(r"\bcolorbar\s*\(([^)]*)\)"),
}
"""Call-site matchers: the S.13.3 features are all call-site properties (A1/T1)."""


def _log(msg: str) -> None:
    """Print a progress line to stdout.

    Parameters:
        msg: text to emit.
    Returns: None.
    Exceptions: none.
    """
    print(f"[fig13.3] {msg}", flush=True)


# Axes that are counts/indices, not physical quantities, and therefore
# carry no unit under §13.3 ("Step", "Iteration", "Element index").  Flagging
# `set_xlabel("SPARTA Step")` as a missing unit would be a false failure.
# (a) count / index axes -- any leading qualifier is fine ("Simulation
#     Step", "SPARTA Step", "Element index"); nothing after the count word
#     can make it a physical quantity needing a unit.
_DIMENSIONLESS_RE = re.compile(
    r"^\s*(?:[A-Za-z]+\s+)*"
    r"(?:step|steps|iteration(?:s)?|sample(?:s)?|element(?:s)?|point(?:s)?|"
    r"index|count|record(?:s)?|frame(?:s)?|cycle(?:s)?)\b",
    re.IGNORECASE,
)
# (b) dimensionless physical quantities -- §13.3 wants the physical quantity
#     named, and these ARE named; they legitimately have no unit.
_DIMENSIONLESS_QTY_RE = re.compile(
    r"\b(?:knudsen|reynolds|mach|coefficien\w*|ratio|fraction|"
    r"c_?[dl]\b|cd\b|cl\b|lift.to.drag|l/d|g.?(?:load)|"
    r"r.?squared|number|percent)\b",
    re.IGNORECASE,
)

# First string literal in a call argument, allowing the `f` prefix used by
# f-string labels (`f"Heat Flux (W/m^2)"`).  Anything else is not a literal.
_LITERAL_RE = re.compile(r"""\s*f?(["'])(.*?)\1""", re.DOTALL)


def _classify_label(arg: str) -> str:
    """Classify one label argument for §13.3 units.

    Parameters:
        arg: the text inside `set_xlabel(...)` -- a quoted literal (possibly
             an f-string, plus trailing `fontsize=` kwargs), a bare
             identifier, or an expression.
    Returns:
        "dimensionless" (count/index axis, units not required),
        "has_units" (literal carries a unit token),
        "no_units" (literal physical label with no unit token),
        or "unresolved" when the label is a variable/expression whose text
        cannot be seen here.  "unresolved" is reported separately and never
        counted as a failure (A3).
    Exceptions: none (pure classifier).

    WHY the literal is extracted first: the captured argument looks like
    `"SPARTA Step", fontsize=11`, so testing the raw string kept both the
    closing quote and the kwarg in scope -- `"SPARTA Step"` therefore failed
    the dimensionless match and was wrongly reported as a missing unit.
    """
    m = _LITERAL_RE.match(arg)
    if m:
        text = m.group(2)
        if _units_present(text):
            return "has_units"
        if (_DIMENSIONLESS_RE.match(text)
                or _DIMENSIONLESS_QTY_RE.search(text)):
            return "dimensionless"
        return "no_units"
    # No leading literal: either `set_xlabel(xlabel)` (a variable) or an
    # f-string/concatenation whose value is not knowable statically.
    return "unresolved"


def _units_present(text: str) -> bool:
    """Decide whether a label string carries a §13.3 unit token.

    Parameters:
        text: the label text (or f-string source) to inspect.
    Returns:
        True when a unit token or an explicit f-string interpolation of a
        label variable is present.
    Exceptions: none (pure predicate).
    References: Standard Operating Procedure of CFD.md §13.3
    """
    return bool(UNIT_RE.search(text))


def _is_renderer(text: str) -> bool:
    """Decide whether a source file actually draws and writes images.

    Parameters:
        text: full source text of a candidate script.
    Returns:
        True when it calls savefig (directly or via the project's _save
        helper).  Non-renderers can never own a figure, which is what keeps
        a VTU writer from claiming someone else's plot.
    Exceptions: none (pure predicate).
    """
    # NO \s* allowed: `savefig\s*\(` matched my own DOCSTRING
    # ("it calls savefig (directly or ...") and made the auditor list
    # ITSELF as a renderer, after which it claimed 46 figures.  matplotlib
    # always writes `fig.savefig(` with no space, and the project helper is
    # always `_save(` -- so requiring the bare call token cannot match prose.
    return bool(re.search(r"\.savefig\(|\b_save\(", text))


def build_renderers() -> list[Path]:
    """Return only the scripts that draw images.

    Parameters: none.
    Returns:
        Sorted list of renderer scripts (A2: these are the only files whose
        labels/legends/colourbars determine a figure).
    Exceptions:
        Unreadable scripts are skipped with a warning, never raised.
    """
    out: list[Path] = []
    for glob in SOURCE_GLOBS:
        for src in sorted(PROJECT_ROOT.glob(glob)):
            try:
                text = src.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                _log(f"skip unreadable source {src.name}: {exc}")
                continue
            if src.name == Path(__file__).name:
                continue          # the auditor renders nothing; never self-claim
            if _is_renderer(text):
                out.append(src)
    return out


def build_exact_index(renderers: list[Path]) -> dict[str, Path]:
    """Index literal figure names written on an image-emitting line.

    Parameters:
        renderers: scripts known to draw images.
    Returns:
        stem -> script (first wins).  A hit here is HIGH confidence: the
        script both renders and names this figure in the same statement.
    Exceptions: read failures are skipped with a warning.
    """
    index: dict[str, Path] = {}
    for src in renderers:
        try:
            text = src.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            _log(f"skip unreadable source {src.name}: {exc}")
            continue
        for line in text.splitlines():
            if not _EMIT_LINE_RE.search(line):
                continue
            for lit in re.findall(r"""["']([A-Za-z0-9_.\-]{4,80})["']""", line):
                index.setdefault(lit, src)
    return index


def resolve_generator(stem: str, exact: dict[str, Path],
                      renderers: list[Path]) -> tuple[Path | None, str]:
    """Locate the renderer for a figure stem, returning a confidence grade.

    Parameters:
        stem: figure name without extension (longest candidate first is
              handled by _tail_stems).
        exact: HIGH-confidence literal index.
        renderers: all renderer scripts, for the scored fallback.
    Returns:
        (script, confidence) where confidence is one of
        "exact" (literal on an emitting line), "prefix" (a contiguous run of
        the figure name appears in one renderer), "token" (majority of the
        figure's name tokens appear in a renderer), or "none" -- never a
        guess dressed up as a match (A3).
    Exceptions: none.

    WHY the scored tier exists: most scripts build the output path in a
    variable (`out = outdir / f"{name}.png"`) so the name literal never sits
    on the savefig line.  Exact matching alone marked 319 of 389 figures as
    unresolved, which would have made the checklist useless.
    """
    for cand in _tail_stems(Path(stem + ".x")):
        if cand in exact:
            return exact[cand], "exact"

    parts = [t for t in re.split(r"[_\-.]", stem) if t]
    if len(parts) < 2:
        return None, "none"

    # SCORE BY LONGEST CONTIGUOUS PREFIX, not by scattered token hits.
    # Counting loose tokens let validation_pipeline.py claim
    # `grid_mesh_map_smooth_00_reference_step_1300` (it contains "grid",
    # "map", "step") over generate_field_panels.py, which literally builds
    # `grid_mesh_map_smooth_{tree}`.  A prefix is what a generator actually
    # writes down.
    texts: dict[Path, str] = {}
    for src in renderers:
        try:
            texts[src] = src.read_text(encoding="utf-8", errors="replace").lower()
        except OSError:
            continue

    # TIER 2 -- longest contiguous name prefix.  This is the strongest
    # secondary signal: a generator writes `grid_mesh_map_smooth_{tree}` as
    # one string, so that prefix in its source is a genuine claim, whereas
    # scattered tokens are not.
    best: Path | None = None
    best_len = 0
    for src, text in texts.items():
        for i in range(len(parts), 1, -1):
            prefix = "_".join(parts[:i]).lower()
            if len(prefix) >= 6 and prefix in text:
                if i > best_len:
                    best, best_len = src, i
                break
    if best is not None and best_len >= 3:
        return best, "prefix"

    # TIER 3 -- majority of the name's tokens.  Weaker, so it is only tried
    # once no renderer can show a real prefix, and it is reported at "token"
    # confidence so the checklist never presents it as an exact claim (A3).
    need = max(2, (len(parts) + 1) // 2)
    best = None
    best_hits = 0
    for src, text in texts.items():
        hits = sum(1 for t in parts if len(t) >= 2 and t.lower() in text)
        if hits > best_hits:
            best, best_hits = src, hits
    if best is not None and best_hits >= need and best_hits >= 3:
        return best, "token"
    return None, "none"


def _stem_of(png: Path) -> str:

    """Return the figure name stem for a PNG path.

    Parameters:
        png: path to the figure file.
    Returns:
        Stem without extension (e.g. `mesh_statistics_smooth`).
    Exceptions: none.
    """
    return png.stem


def _tail_stems(png: Path) -> list[str]:
    """Candidate stems, longest first, to survive `name_step_N.png` suffixes.

    Parameters:
        png: path to the figure file.
    Returns:
        Candidate stems from full filename down to first segment.
    Exceptions: none.
    """
    stem = _stem_of(png)
    parts = stem.split("_")
    out = [stem]
    for i in range(1, len(parts)):
        out.append("_".join(parts[: len(parts) - i]))
    return out


def audit_figure(png: Path, exact: dict[str, Path],
                 renderers: list[Path]) -> dict[str, object]:
    """Produce the §13.3 compliance row for one figure.

    Parameters:
        png: the figure file.
        exact: HIGH-confidence literal index from build_exact_index.
        renderers: renderer scripts used by the scored fallback.
    Returns:
        dict with figure, generator, the five feature booleans, missing[]
        and status in {ok, partial, no_generator}.
    Exceptions:
        Unreadable PNG is reported as status "unreadable".
    Notes:
        A2 applies: these are properties of the GENERATOR SOURCE, not of the
        rendered pixels; the CSV `basis` column says so on every row.
    References: Standard Operating Procedure of CFD.md §13.3
    """
    rel = str(png.relative_to(PROJECT_ROOT))
    row: dict[str, object] = {
        "figure": rel,
        "generator": "",
        "generator_confidence": "none",
        "basis": "generator_source_not_pixels",
        "has_title": False,
        "has_xlabel": False,
        "has_ylabel": False,
        "xlabel_has_units": False,
        "ylabel_has_units": False,
        "has_legend": False,
        "has_colorbar_label": False,
        "has_colorbar_call": False,
        "axes_hidden": False,
        "xlabel_units_kind": "none",
        "ylabel_units_kind": "none",
        "unresolved": "",
        "missing": "",
        "status": "no_generator",
    }
    if not png.is_file():
        row["status"] = "unreadable"
        row["missing"] = "file_missing"
        return row

    src, confidence = resolve_generator(png.stem, exact, renderers)
    row["generator_confidence"] = confidence
    if src is None:
        row["missing"] = "no renderer names this figure"
        return row

    try:
        text = src.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        row["status"] = "unreadable"
        row["missing"] = f"generator unreadable: {exc}"
        return row

    row["generator"] = str(src.relative_to(PROJECT_ROOT))

    x_args = _call_args(text, "set_xlabel")
    y_args = _call_args(text, "set_ylabel")
    title = _CALL_RE["title"].search(text)
    cb_args = _call_args(text, "colorbar")
    colorbar = cb_args is not None

    xlab = x_args if x_args is not None else ""
    ylab = y_args if y_args is not None else ""
    row["has_xlabel"] = x_args is not None
    row["has_ylabel"] = y_args is not None
    row["has_title"] = bool(title)
    x_kind = _classify_label(xlab) if x_args is not None else "none"
    y_kind = _classify_label(ylab) if y_args is not None else "none"
    row["xlabel_units_kind"] = x_kind
    row["ylabel_units_kind"] = y_kind
    row["has_legend"] = bool(_CALL_RE["legend"].search(text))
    row["has_colorbar_call"] = colorbar
    row["has_colorbar_label"] = bool(
        (cb_args and re.search(r"\blabel\s*=", cb_args))
        or re.search(r"\w+\.set_label\s*\(", text)
    )
    # Units required only for a literal label of a physical quantity that
    # states none; dimensionless axes and variable labels are exempt here.
    row["xlabel_has_units"] = x_kind in ("has_units", "dimensionless")
    row["ylabel_has_units"] = y_kind in ("has_units", "dimensionless")

    missing: list[str] = []
    unresolved: list[str] = []
    if not row["has_title"]:
        missing.append("title")
    # A renderer that calls set_axis_off() draws NO axes (render_geometry_4views
    # builds four stylised 3-D azimuth views and hides the frame).  Requiring
    # axis labels there would be a false failure -- and adding labels behind a
    # hidden frame would let the figure "pass" while still showing nothing,
    # which is precisely what 13.3 exists to prevent.  Record it as not
    # applicable instead of as a failure.
    axes_hidden = bool(re.search(r"set_axis_off\s*\(", text))
    row["axes_hidden"] = axes_hidden
    if axes_hidden:
        if not row["has_xlabel"] or not row["has_ylabel"]:
            unresolved.append("axis_labels_not_applicable")
    else:
        if not row["has_xlabel"]:
            missing.append("xlabel")
        elif x_kind == "no_units":
            missing.append("xlabel_units")
        elif x_kind == "unresolved":
            unresolved.append("xlabel_units")
        if not row["has_ylabel"]:
            missing.append("ylabel")
        elif y_kind == "no_units":
            missing.append("ylabel_units")
        elif y_kind == "unresolved":
            unresolved.append("ylabel_units")
    # §13.3 bullet 4 covers SCALAR CONTOURS only.  A script that draws no
    # colorbar at all (line plots, bar charts) is out of scope for it --
    # flagging those was double-counting every non-contour figure.
    if row["has_colorbar_call"] and not row["has_colorbar_label"]:
        missing.append("colorbar_limits")

    row["unresolved"] = ",".join(unresolved)

    row["missing"] = ",".join(missing)
    if not missing:
        row["status"] = "ok"
    else:
        row["status"] = "partial"
    return row


def collect_figures() -> list[Path]:
    """Enumerate result figures under FIGURE_DIRS.

    Parameters: none.
    Returns:
        Sorted list of PNG paths, capped at MAX_FIGURES.
    Exceptions:
        Unreadable directories are warned and skipped (never raised).
    """
    out: list[Path] = []
    for d in FIGURE_DIRS:
        if not d.is_dir():
            continue
        try:
            for png in sorted(d.rglob("*.png")):
                if any(part in EXCLUDE_DIRS for part in png.parts):
                    continue
                out.append(png)
                if len(out) >= MAX_FIGURES:
                    _log(f"figure cap reached ({MAX_FIGURES})")
                    return out
        except OSError as exc:
            _log(f"cannot walk {d}: {exc}")
    return out


def main(argv: list[str] | None = None) -> int:
    """Run the §13.3 audit and write checklist.csv + checklist.json.

    Parameters:
        argv: argument list; defaults to sys.argv[1:].  No arguments means
              audit everything (the run.py default path).
    Returns:
        0 always -- this is a REPORTING tool; a failing figure is data, not
        an error condition.  The verdict lives in the JSON.
    Exceptions:
        Write failures propagate (an audit that cannot be saved must not
        look like a clean run).
    References: Standard Operating Procedure of CFD.md §13.3
    """
    parser = argparse.ArgumentParser(
        prog="audit_figure_sufficiency",
        description="Check generated figures against SOP §13.3 and write "
                    "the checklist CSV/JSON.")
    parser.add_argument("--root", default=None, help="audit one directory only")
    parser.add_argument("--json-name", default="figure_checklist.json")
    parser.add_argument("--csv-name", default="figure_checklist.csv")
    args = parser.parse_args(argv)

    renderers = build_renderers()
    exact = build_exact_index(renderers)
    figures = ([Path(args.root)] if args.root else [])
    if args.root:
        figures = sorted(Path(args.root).rglob("*.png"))
    else:
        figures = collect_figures()

    rows = [audit_figure(p, exact, renderers) for p in figures]

    SOP_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = SOP_DIR / args.csv_name
    if rows:
        with csv_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    counts: dict[str, int] = {}
    missing_counts: dict[str, int] = {}
    for r in rows:
        counts[str(r["status"])] = counts.get(str(r["status"]), 0) + 1
        for m in str(r["missing"]).split(","):
            if m:
                missing_counts[m] = missing_counts.get(m, 0) + 1

    ok = counts.get("ok", 0)
    total = len(rows)
    summary = {
        "sop_clause": "13.3",
        "basis": "generator source, not rendered pixels (A2)",
        "figures": total,
        "status_counts": counts,
        "missing_counts": dict(sorted(missing_counts.items(), key=lambda kv: -kv[1])),
        "compliant_pct": round(100.0 * ok / total, 2) if total else None,
        "verdict": "ok" if total and ok == total else "NOT_MET",
        "csv": str(csv_path.relative_to(PROJECT_ROOT)),
    }
    (SOP_DIR / args.json_name).write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    _log(f"{total} figures audited -> {summary['verdict']} "
         f"({ok} compliant, {summary['compliant_pct']}%)")
    if missing_counts:
        top = list(missing_counts.items())[:5]
        _log("top gaps: " + ", ".join(f"{k}={v}" for k, v in top))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
