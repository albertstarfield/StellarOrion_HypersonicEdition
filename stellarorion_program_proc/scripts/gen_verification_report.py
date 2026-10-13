#!/usr/bin/env python3
"""
===============================================================================
SCRIPT: gen_verification_report.py — Coq proof-corpus status-table generator
===============================================================================

Keeps the generated status section of docs/verification_report.tex in sync
with the real Coq/Rocq proof corpus. Scans the .v sources, extracts every
proof-bearing declaration (Lemma / Theorem / Corollary / Proposition / Fact)
and its statement, merges the coqc verdicts from the pipeline gate's JSON,
and rewrites ONLY the region between the ``% BEGIN GENERATED`` and
``% END GENERATED`` sentinels in the LaTeX file. Hand-written prose is never
touched, so regeneration is idempotent.

AXIOMS:
    A1: A .v file's proof obligations are exactly its comment-stripped
        ``Lemma``/``Theorem``/``Corollary``/``Proposition``/``Fact``
        declarations; ``Definition`` declarations are models, not obligations.
    A2: A statement whose entire proposition is the literal ``True`` is a
        transparent placeholder, not a proof of the unit's real property;
        it is counted separately and disclosed, never hidden.
    A3: ``Admitted`` terminates a proof without discharging it; coqc still
        exits 0 on such a file, so "compiles" is never reported as "proved".
    A4: The coqc verdict column is sourced ONLY from the gate JSON; when the
        JSON is absent the column reads "not gated" rather than guessing.

THEORIES:
    T1: Comment-stripping before declaration scanning makes the counts
        immune to prose mentions (e.g. headers that say "Qed replaces
        Admitted"), which would otherwise inflate the tallies.
    T2: Statement capture runs to the first statement-final period at
        parenthesis depth zero followed by a newline, so multi-line
        forall statements are kept whole while decimal points (0.5) and
        periods inside terms are never mistaken for the terminator.

APPLICATIONS:
    python3 scripts/gen_verification_report.py                      # refresh .tex
    python3 scripts/gen_verification_report.py --status results/coqc_status.json
    python3 scripts/gen_verification_report.py --dry-run            # print, no write

CONTRACT — coqc status JSON (produced by the pipeline gate):
    Either a bare list of records, or an object whose value under one of
    the keys "results" / "files" / "coqc" is that list. Each record:
        {"path": "proofs/hiad_geometry.v",   # repo-relative (or absolute,
                                             # or project-prefixed) path
         "ok": true,                          # bool: coqc exit status
         "error_snippet": "..."}              # optional: first error lines
    Tolerated aliases: "status" in {"pass", "fail", "ok", "error"},
    "returncode" (int, 0 == ok), "error" as an alias of error_snippet.
    A missing file, an empty file, or malformed JSON is NOT an error: every
    verdict degrades to "not gated" and the reason is printed to stderr.
    Use --strict to turn an unreadable/garbled status file into exit 1.

CITATIONS:
    [1] Coq Reference Manual — https://coq.inria.fr/refman/
    [2] code-quality.md validation-pipeline order (source of truth for the
        gate placement; coqc gate belongs after gnatprove/gnatcov and before
        the sabotage verifier).
===============================================================================
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Layout constants — every path is discovered from this file, never hardcoded.
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROOF_DIRS: tuple[Path, ...] = (Path("proofs"), Path("src/proofs"), Path("src/rocq"))
DEFAULT_TEX = PROJECT_ROOT / "docs" / "verification_report.tex"
DEFAULT_STATUS = PROJECT_ROOT / "results" / "coqc_status.json"

BEGIN_SENTINEL = "% BEGIN GENERATED"
END_SENTINEL = "% END GENERATED"
SENTINEL_NOTE = (
    "% Regenerate with: python3 scripts/gen_verification_report.py"
    " --status results/coqc_status.json"
)

# ---------------------------------------------------------------------------
# Extraction patterns.
# DECLARATION_RE: A1 — the proof-bearing vernac keywords, case-sensitive as
# Coq vernacular, anchored at line start with optional indentation (Sections
# indent their bodies).
# ---------------------------------------------------------------------------
DECLARATION_RE = re.compile(
    r"^[ \t]*(Theorem|Lemma|Corollary|Proposition|Fact)"
    r"[ \t]+([A-Za-z_][A-Za-z0-9_']*)[ \t]*:",
    re.MULTILINE,
)
ADMITTED_RE = re.compile(r"^[ \t]*Admitted[ \t]*\.", re.MULTILINE)
PLACEHOLDER_STATEMENTS = {"True", "True."}


@dataclass(frozen=True)
class Declaration:
    """One proof-bearing declaration extracted from a .v file."""

    kind: str
    name: str
    statement: str
    line: int


@dataclass(frozen=True)
class Verdict:
    """The gate verdict for one file, plus an optional failure excerpt."""

    ok: bool
    error_snippet: str
    gated: bool


# ---------------------------------------------------------------------------
# LaTeX escaping.
# WHY THIS FUNCTION EXISTS: table cells are composed in text mode, and proof
# paths/statements are full of underscores (stellarorion_ffi.v) which TeX
# reads as a subscript switch; without escaping the longtable fails to
# compile. Backslash is escaped first so later replacements cannot double-
# escape it.
# ---------------------------------------------------------------------------
_TEX_SPECIALS = ("\\", "&", "%", "$", "#", "_", "{", "}", "~", "^")


def tex_escape(text: str) -> str:
    """Escape the LaTeX special characters that are illegal in text mode.

    Args:
        text: Raw string (Coq path, identifier, or statement).

    Returns:
        The same string with \\, &, %, $, #, _, {, }, ~, ^ backslash-escaped.

    Raises:
        Nothing.
    """
    out = text
    for ch in _TEX_SPECIALS:
        out = out.replace(ch, "\\" + ch)
    return out


def strip_coq_comments(text: str) -> str:
    """Remove Coq block comments, honouring nesting, leaving newlines intact.

    WHY: T1 — headers legitimately say "Qed replaces Admitted" inside
    comments; scanning raw text would miscount them as real obligations.

    Args:
        text: Full .v file contents.

    Returns:
        The file contents with every ``(* ... *)`` comment replaced by a
        single space (comment interiors may span lines; line count is kept
        by substituting each interior newline).

    Raises:
        Nothing. Unterminated comments simply run to end of text, which is
        the same behaviour Coq's lexer reports an error for later.
    """
    out: list[str] = []
    depth = 0
    i = 0
    n = len(text)
    while i < n:
        two = text[i : i + 2]
        if depth == 0:
            if two == "(*":
                depth = 1
                out.append(" ")
                i += 2
                continue
            out.append(text[i])
            i += 1
        else:
            if two == "(*":
                depth += 1
                i += 2
                continue
            if two == "*)":
                depth -= 1
                out.append(" ")
                i += 2
                continue
            # Keep line structure so declaration line numbers stay honest.
            out.append("\n" if text[i] == "\n" else " ")
            i += 1
    return "".join(out)


def extract_declarations(text: str) -> list[Declaration]:
    """Extract every proof-bearing declaration and its statement.

    Implements T2: the statement runs from after the declaring colon to the
    first ``.`` at parenthesis depth zero that is followed by a newline (or
    end of text). That keeps ``forall a b : R, 0 <= a -> a * b.`` whole while
    never cutting inside decimal literals like ``0.5 <= 3.0``.

    Args:
        text: Raw .v file contents (comments are stripped internally).

    Returns:
        Declarations in file order, each carrying kind, name, statement
        (whitespace-normalised) and 1-based line number.

    Raises:
        Nothing.
    """
    code = strip_coq_comments(text)
    declarations: list[Declaration] = []
    for match in DECLARATION_RE.finditer(code):
        kind, name = match.group(1), match.group(2)
        line = code.count("\n", 0, match.start()) + 1
        # Walk the statement from the match end at paren depth 0.
        i = match.end()
        depth = 0
        end = len(code)
        while i < len(code):
            ch = code[i]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth = max(0, depth - 1)
            elif ch == "." and depth == 0:
                nxt = code[i + 1] if i + 1 < len(code) else "\n"
                rest = code[i + 1 : i + 3]
                if nxt == "\n" or rest.strip() == "" or nxt == " ":
                    # T2: a '.' followed only by newline/space ends the
                    # statement; a '.' followed by a digit is a decimal.
                    end = i + 1
                    break
            i += 1
        statement = " ".join(code[match.end() : end].split())
        declarations.append(
            Declaration(kind=kind, name=name, statement=statement, line=line)
        )
    return declarations


def count_admitted(text: str) -> int:
    """Count proof-terminating ``Admitted.`` commands, comments excluded.

    Args:
        text: Raw .v file contents.

    Returns:
        Number of ``Admitted.`` vernacular commands outside comments.

    Raises:
        Nothing.
    """
    return len(ADMITTED_RE.findall(strip_coq_comments(text)))


def read_status(path: Path, strict: bool) -> dict[str, Verdict]:
    """Read and normalise the coqc gate status JSON.

    Contract is documented in the module docstring: a bare list of records
    or an object wrapping such a list under "results"/"files"/"coqc".
    Path keys are normalised to repo-relative POSIX form so the gate may
    emit absolute, project-prefixed, or repo-relative paths.

    Args:
        path: JSON file to read.
        strict: When True, unreadable or malformed content raises SystemExit
            instead of degrading to "not gated".

    Returns:
        Mapping of repo-relative .v path -> Verdict. Empty mapping means
        "no gate data", which callers render as "not gated".

    Raises:
        SystemExit: If strict is True and the file exists but cannot be
            parsed into the documented shape.
    """
    problem = ""
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        problem = f"cannot read/parse {path}: {exc}"
        payload = None
    if payload is not None:
        records = payload
        if isinstance(payload, dict):
            for key in ("results", "files", "coqc"):
                if isinstance(payload.get(key), list):
                    records = payload[key]
                    break
            else:
                problem = f"{path}: no 'results'/'files'/'coqc' list found"
                records = None
        if isinstance(records, list):
            verdicts: dict[str, Verdict] = {}
            for entry in records:
                if not isinstance(entry, dict):
                    continue
                raw_path = entry.get("path") or entry.get("file") or ""
                if not raw_path:
                    continue
                rel = normalise_path(raw_path)
                if rel is None:
                    continue
                verdicts[rel] = _record_to_verdict(entry)
            if verdicts or not records:
                return verdicts
    if strict:
        print(f"gen_verification_report: {problem or 'empty status payload'}", file=sys.stderr)
        raise SystemExit(1)
    if problem:
        print(f"gen_verification_report: WARNING {problem}", file=sys.stderr)
        print("gen_verification_report: WARNING falling back to 'not gated'", file=sys.stderr)
    return {}


def normalise_path(raw_path: str) -> str | None:
    """Normalise any of the accepted spellings of a .v path.

    WHY: the pipeline gate may run from the repo root (``stellarorion_
    program_proc/proofs/x.v``) or from the project root (``proofs/x.v``);
    both must join against the corpus scan keys.

    Args:
        raw_path: Path string from the status JSON.

    Returns:
        Repo-relative POSIX path if it points inside a known proof
        directory, else None (unknown paths are ignored, not fatal).

    Raises:
        Nothing.
    """
    candidate = Path(raw_path)
    if candidate.is_absolute():
        try:
            candidate = candidate.resolve().relative_to(PROJECT_ROOT)
        except ValueError:
            return None
    parts = candidate.parts
    if parts and parts[0] == PROJECT_ROOT.name:
        parts = parts[1:]
    rel = "/".join(parts)
    for proof_dir in PROOF_DIRS:
        prefix = proof_dir.as_posix() + "/"
        if rel.startswith(prefix):
            return rel
    return None


def _record_to_verdict(entry: dict[str, object]) -> Verdict:
    """Coerce one status record into a Verdict (aliases tolerated).

    Args:
        entry: Mapping with "ok", or aliases "status"/"returncode".

    Returns:
        Verdict with ok=True for pass, ok=False for fail, plus the error
        snippet (possibly empty). Missing/unknown shapes default to
        gated=True, ok=False (loud, never silently "pass").

    Raises:
        Nothing.
    """
    snippet = str(entry.get("error_snippet") or entry.get("error") or "")
    if isinstance(entry.get("ok"), bool):
        ok = entry["ok"]
    elif isinstance(entry.get("returncode"), int):
        ok = entry["returncode"] == 0
    elif isinstance(entry.get("status"), str):
        ok = entry["status"].lower() in ("pass", "ok", "success", "passed")
    else:
        ok = False
        snippet = snippet or "malformed status record (no ok/status/returncode)"
    return Verdict(ok=ok, error_snippet=snippet, gated=True)


def scan_corpus() -> list[tuple[str, list[Declaration], int, int]]:
    """Enumerate the .v corpus and extract declarations, placeholders, admits.

    Returns rows of (repo-relative POSIX path, declarations,
    admitted_count, placeholder_count). Paths use pathlib globbing directly
    so .gitignored directories (proofs/ is gitignored in this repo) are
    still covered — the generator must not depend on git visibility.

    Returns:
        List of rows sorted by path (proofs/ before src/ before src/rocq by
        natural string order).

    Raises:
        SystemExit: If a proof directory is missing entirely (a structural
        surprise worth failing loudly about).
    """
    rows: list[tuple[str, list[Declaration], int, int]] = []
    for proof_dir in PROOF_DIRS:
        absolute_dir = PROJECT_ROOT / proof_dir
        if not absolute_dir.is_dir():
            print(
                f"gen_verification_report: ERROR proof directory missing: "
                f"{absolute_dir}",
                file=sys.stderr,
            )
            raise SystemExit(1)
        for path in sorted(absolute_dir.glob("*.v")):
            text = path.read_text(encoding="utf-8", errors="replace")
            declarations = extract_declarations(text)
            admitted = count_admitted(text)
            placeholders = sum(
                1 for d in declarations if d.statement.strip() in PLACEHOLDER_STATEMENTS
            )
            rel = f"{proof_dir.as_posix()}/{path.name}"
            rows.append((rel, declarations, admitted, placeholders))
    rows.sort(key=lambda row: row[0])
    return rows


def _verdict_cell(verdict: Verdict | None) -> str:
    """Render one verdict cell; never claims what the gate did not measure."""
    if verdict is None:
        return "not gated"
    return "pass" if verdict.ok else "FAIL"


def render_fragment(
    rows: list[tuple[str, list[Declaration], int, int]],
    verdicts: dict[str, Verdict],
    source_status: Path | None,
) -> str:
    """Render the whole generated region (longtable + verbatim inventory).

    The longtable columns are: File, Proofs, Placeholders, Admitted, coqc
    verdict. The verbatim inventory lists every declaration with its source
    line so the report's prose can be diffed against reality mechanically.

    Args:
        rows: Corpus rows from scan_corpus().
        verdicts: Normalised gate verdicts (possibly empty).
        source_status: Path passed via --status, or None.

    Returns:
        The fragment text to place between the sentinels.

    Raises:
        Nothing.
    """
    lines: list[str] = []
    total_proofs = sum(len(r[1]) for r in rows)
    total_placeholders = sum(r[3] for r in rows)
    total_admitted = sum(r[2] for r in rows)
    gated = sum(1 for r in rows if normalise_path(r[0]) in verdicts)
    lines.append(
        f"% {len(rows)} files, {total_proofs} proof obligations, "
        f"{total_placeholders} placeholders, {total_admitted} Admitted, "
        f"{gated} gated rows"
    )
    lines.append(f"% Status source: {source_status if source_status else 'none (not gated)'}")
    lines.append(SENTINEL_NOTE)
    lines.append(r"\begingroup")
    lines.append(r"\footnotesize")
    lines.append(r"\setlength{\LTleft}{0pt}")
    lines.append(r"\setlength{\LTright}{0pt}")
    lines.append(r"\begin{longtable}{@{}lrrrl@{}}")
    lines.append(r"\caption{Coq/Rocq proof corpus: obligations, placeholders, "
                 r"\texttt{Admitted} counts and \texttt{coqc} verdicts. "
                 r"``not gated'' means the pipeline gate JSON was not supplied; "
                 r"compile success is never reported as proof success.}")
    lines.append(r"\label{tab:cocorpus}\\")
    lines.append(r"\toprule")
    lines.append(r"\textbf{File} & \textbf{Proofs} & \textbf{Placeh.} & "
                 r"\textbf{Adm.} & \textbf{coqc verdict} \\")
    lines.append(r"\midrule")
    lines.append(r"\endfirsthead")
    lines.append(r"\multicolumn{5}{@{}l}{\footnotesize\emph{Table \ref{tab:cocorpus} (continued)}}\\")
    lines.append(r"\toprule")
    lines.append(r"\textbf{File} & \textbf{Proofs} & \textbf{Placeh.} & "
                 r"\textbf{Adm.} & \textbf{coqc verdict} \\")
    lines.append(r"\midrule")
    lines.append(r"\endhead")
    lines.append(r"\midrule")
    lines.append(r"\multicolumn{5}{r@{}}{\footnotesize\emph{continued on next page}}\\")
    lines.append(r"\endfoot")
    lines.append(r"\bottomrule")
    lines.append(r"\endlastfoot")
    for rel, declarations, admitted, placeholders in rows:
        key = normalise_path(rel) or rel
        verdict = _verdict_cell(verdicts.get(key))
        lines.append(
            f"\\texttt{{{tex_escape(rel)}}} & {len(declarations)} & "
            f"{placeholders} & {admitted} & {verdict} \\\\"
        )
    lines.append(r"\end{longtable}")
    lines.append(r"\endgroup")
    lines.append("")
    lines.append(r"\subsection*{Generated theorem inventory}")
    lines.append(
        r"\emph{Extracted verbatim from each \texttt{.v} file's declarations; "
        r"statements marked \texttt{.:\ True} are the disclosed placeholders of "
        r"the corpus.}"
    )
    lines.append(r"\begin{verbatim}")
    for rel, declarations, _admitted, _placeholders in rows:
        lines.append(rel)
        for declaration in declarations:
            statement = declaration.statement.replace("\\end{verbatim}", "")
            lines.append(
                f"  [{declaration.line}] {declaration.kind} "
                f"{declaration.name} : {statement}"
            )
    lines.append(r"\end{verbatim}")
    return "\n".join(lines) + "\n"


def update_tex(tex_path: Path, fragment: str) -> bool:
    """Replace the text between the sentinels, leaving prose untouched.

    Idempotent: replacing with an identical fragment is a no-op.

    Args:
        tex_path: The .tex document to update in place.
        fragment: Rendered generated region (sentinels themselves preserved).

    Returns:
        True if the file was written, False if it already matched.

    Raises:
        SystemExit: If the file is missing, sentinels are missing/duplicated,
            or the end sentinel precedes the begin sentinel.
    """
    if not tex_path.is_file():
        print(
            f"gen_verification_report: ERROR {tex_path} does not exist; "
            "create it with the BEGIN/END GENERATED sentinels first.",
            file=sys.stderr,
        )
        raise SystemExit(1)
    text = tex_path.read_text(encoding="utf-8")
    begin = text.find(BEGIN_SENTINEL)
    end = text.find(END_SENTINEL)
    if begin == -1 or end == -1 or end < begin:
        print(
            f"gen_verification_report: ERROR {tex_path} must contain "
            f"'{BEGIN_SENTINEL}' followed by '{END_SENTINEL}'.",
            file=sys.stderr,
        )
        raise SystemExit(1)
    updated = (
        text[: begin + len(BEGIN_SENTINEL)]
        + "\n"
        + fragment.rstrip("\n")
        + "\n"
        + text[end:]
    )
    if updated == text:
        return False
    tex_path.write_text(updated, encoding="utf-8")
    return True


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Argument vector (defaults to sys.argv[1:]).

    Returns:
        Parsed namespace with tex, status, strict and dry_run.

    Raises:
        SystemExit: On --help or an invalid flag (argparse behaviour).
    """
    parser = argparse.ArgumentParser(
        description=(
            "Regenerate the generated section of docs/verification_report.tex "
            "from the Coq proof corpus and the coqc gate status JSON."
        )
    )
    parser.add_argument(
        "--tex",
        type=Path,
        default=DEFAULT_TEX,
        help=f"LaTeX file to update (default: {DEFAULT_TEX}).",
    )
    parser.add_argument(
        "--status",
        type=Path,
        default=DEFAULT_STATUS,
        help=(
            "coqc gate status JSON (default: results/coqc_status.json). "
            "A missing file is fine: verdicts render as 'not gated'."
        ),
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 when the status file exists but is unreadable/malformed.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the generated fragment to stdout instead of editing the .tex.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Entry point: scan, read gate data, render, and update the document.

    Args:
        argv: Argument vector for testability.

    Returns:
        Process exit code (0 on success, 1 under --strict with bad input).

    Raises:
        SystemExit: Propagated from helpers on structural errors.
    """
    args = parse_args(argv)
    rows = scan_corpus()
    verdicts = read_status(args.status, strict=args.strict)
    # WHY: the fragment must not advertise a status file that does not exist.
    # When the gate has not produced its JSON yet, the honest rendering is
    # "none (not gated)", which is also what a first-time reader sees.
    status_source: Path | None = args.status if args.status.is_file() else None
    fragment = render_fragment(rows, verdicts, status_source)
    if args.dry_run:
        sys.stdout.write(fragment)
        return 0
    changed = update_tex(args.tex, fragment)
    total = sum(len(row[1]) for row in rows)
    print(
        f"gen_verification_report: {len(rows)} .v files, {total} obligations; "
        f"{args.tex} {'updated' if changed else 'already up to date'}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
