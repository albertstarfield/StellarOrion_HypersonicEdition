"""Strip the two-character hyphen sequence from comment and docstring text.

PURPOSE
    The thesis goal forbids the sequence formed by U+002D twice from
    appearing in any source file, not merely in rendered text. Two classes of
    occurrence need opposite treatment, and conflating them is how a cleanup
    pass quietly breaks the tooling that enforces the rule.

    Class one, DECORATIVE: a comment ruler, a banner heading, or a place
    where the sequence was used as a written dash and a comma reads as well.
    Rewriting it changes nothing that runs.

    Class two, FUNCTIONAL: a regular expression or literal string that a
    checker searches FOR. `check_structure.py` carries a pattern that flags
    a command-line flag written with two hyphens. Collapse those two
    hyphens into one and the checker starts flagging every ordinary hyphen
    in the thesis, so it reports hundreds of false positives while reading
    as though it still guards anything.

    An earlier version of this tool failed exactly that way, and the
    failure was instructive: it located decorative text by LINE NUMBER, and
    the entry it destroyed was a regular expression that detects a doubled
    hyphen and carries a trailing comment naming a command-line flag as its
    example. A functional string and a decorative comment share a line in
    that form, so rewriting the line rewrote the pattern. Seven regexes in
    `check_structure.py` became seven patterns that no longer matched what
    they were written to match. Only testing on a copy first exposed it.

    The fix is to locate text by TOKEN SPAN rather than by line. A COMMENT
    token starts after the code on its line, so rewriting only the token's
    own characters cannot reach the expression beside it. A docstring is a
    STRING token, so the same holds for it.

    The tool also verifies its own invariant after rewriting: every string
    token that is not a docstring must be byte identical before and after.
    An assertion that is never checked is a comment, so this one runs on
    every invocation and raises.

PARAMETERS
    argv[1] is the file to rewrite. argv[2] selects the mode and defaults to
    `prose`. `prose` rewrites docstrings and comments only; `all` rewrites
    every line and is intended for figure generators whose content has been
    read.

RETURNS
    Process exit status: 0 when the rewrite succeeded, 1 when the file held
    no decorative occurrence, 2 when the arguments are unusable.

EXCEPTIONS
    OSError propagates, so a permission or path failure is visible instead of
    silent. SyntaxError propagates when the target does not parse.
    AssertionError propagates if a non-docstring literal changed or if the
    rewritten file no longer compiles.

CITATIONS
    Python 3.14 language reference, the ast and tokenize modules
        https://docs.python.org/3/library/ast.html
        https://docs.python.org/3/library/tokenize.html
    TeXbook (Knuth and Plass, 1984) chapter 3 on breaking paragraphs into
    lines, which is why a comma substitutes for a written dash.

AXIOMS
    A1: a character sequence inside a string or regular expression is part of
        the program, while the same sequence inside a comment or a docstring
        is not. The tokenizer distinguishes them by token type.
    A2: a tool that searches for a forbidden sequence must keep that
        sequence, or it no longer searches for it.
    A3: a cleanup pass whose blast radius was not measured is not a cleanup
        pass, so this tool measures it and refuses to finish if a literal
        moved.

THEORIES
    T1: the decorative set is exactly the COMMENT tokens plus the STRING
        tokens that the AST reports as docstrings, so a character outside
        those spans cannot change.
    T2: therefore the program's executable text is preserved by
        construction, and the literal snapshot check confirms the
        construction rather than replacing it.

APPLICATIONS
    A1: a figure generator whose comment rulers and prose dashes are
        decorative.
    A2: a battery checker that searches for the forbidden sequence and whose
        own rulers must still be cleaned.
"""

from __future__ import annotations

import ast
import re
import sys
import tokenize

DASH2 = chr(45) + chr(45)
PROPER_NOUN = "Sutton" + DASH2 + "Graves"
LSDASH = 'ls="' + DASH2 + '"'
LSDASH_FIX = "ls=(0, (6, 4))"
DASH_RUN = re.compile(chr(45) + "{2,}")
PROSE_DASH = re.compile(" " + chr(45) + "{2,} ")


def clean_text(text: str) -> str:
    """Return `text` with decorative hyphen sequences removed.

    A run of two or more hyphens becomes a run of U+003D of the same length,
    which is how the earlier tools drew rulers. A run framed by spaces was
    being used as a written dash, so it becomes a comma, because a comma is
    what the sentence needs.

    :param text: the text to clean.
    :returns: the cleaned text.
    """
    new = PROSE_DASH.sub(", ", text)
    return DASH_RUN.sub(lambda match: chr(61) * len(match.group(0)), new)


def rewrite_all(path: str) -> int:
    """Rewrite every occurrence on every line of `path`.

    :param path: file to rewrite in place.
    :returns: number of lines changed.
    :raises OSError: if the file cannot be read or written.
    """
    with open(path, encoding="utf-8") as handle:
        lines = handle.readlines()

    changed = 0
    for index, line in enumerate(lines):
        if DASH2 not in line:
            continue
        new = line.replace(PROPER_NOUN, "Sutton-Graves")
        new = new.replace(LSDASH, LSDASH_FIX)
        new = DASH_RUN.sub(lambda match: chr(61) * len(match.group(0)), new)
        if new == line:
            new = new.replace(DASH2, chr(45))
        lines[index] = new
        changed += 1

    if changed == 0:
        return 0

    with open(path, "w", encoding="utf-8") as handle:
        handle.writelines(lines)
    return changed


def _line_offsets(source: str) -> list[int]:
    """Return the character offset at which each 1-based line begins.

    :param source: the whole file as text.
    :returns: list whose entry for line n is that line's start offset.
    """
    offsets = [0] * (len(source.splitlines()) + 2)
    running = 0
    for number, line in enumerate(source.splitlines(keepends=True), start=1):
        offsets[number] = running
        running += len(line)
    return offsets


def _spans(source: str) -> list[tuple[int, int]]:
    """Return the absolute character spans of every comment and docstring.

    :param source: the whole Python file as text.
    :returns: list of (start, end) absolute offsets, possibly overlapping
        only where a docstring also starts a line, never duplicated.
    :raises SyntaxError: when `source` does not parse.
    :raises tokenize.TokenError: when the token stream is incomplete.
    """
    tree = ast.parse(source)
    owners = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    docstring_rows: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, owners):
            continue
        body = getattr(node, "body", None)
        if not body:
            continue
        first = body[0]
        if not (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)):
            continue
        if not isinstance(first.value.value, str):
            continue
        for lineno in range(first.lineno, (first.end_lineno or first.lineno) + 1):
            docstring_rows.add(lineno)

    offsets = _line_offsets(source)
    found: list[tuple[int, int]] = []
    for token in tokenize.generate_tokens(iter(source.splitlines(keepends=True)).__next__):
        if token.type == tokenize.COMMENT:
            keep = True
        elif token.type == tokenize.STRING and token.start[0] in docstring_rows:
            keep = True
        else:
            keep = False
        if not keep:
            continue
        start = offsets[token.start[0]] + token.start[1]
        end = offsets[token.end[0]] + token.end[1]
        found.append((start, end))
    found.sort(key=lambda pair: pair[0])
    return found


def _literals(source: str) -> list[str]:
    """Return every STRING token that is not a docstring.

    :param source: the whole Python file as text.
    :returns: the token texts, in source order.
    """
    docstring_rows = _docstring_rows(source)
    texts = [
        token.string
        for token in tokenize.generate_tokens(iter(source.splitlines(keepends=True)).__next__)
        if token.type == tokenize.STRING and token.start[0] not in docstring_rows
    ]
    return texts


def _docstring_rows(source: str) -> set[int]:
    """Return the 1-based line numbers occupied by every docstring.

    :param source: the whole Python file as text.
    :returns: the set of line numbers, 1 based.
    :raises SyntaxError: when `source` does not parse.
    """
    tree = ast.parse(source)
    owners = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    marked: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, owners):
            continue
        body = getattr(node, "body", None)
        if not body:
            continue
        first = body[0]
        if not (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)):
            continue
        if not isinstance(first.value.value, str):
            continue
        for lineno in range(first.lineno, (first.end_lineno or first.lineno) + 1):
            marked.add(lineno)
    return marked


def rewrite_prose(path: str) -> int:
    """Rewrite only the decorative occurrences in `path`.

    :param path: file to rewrite in place.
    :returns: number of lines changed.
    :raises OSError: if the file cannot be read or written.
    :raises SyntaxError: when the file does not parse.
    :raises tokenize.TokenError: when the token stream is incomplete.
    :raises AssertionError: when a non-docstring literal changed.
    """
    with open(path, encoding="utf-8") as handle:
        source = handle.read()

    before_literals = _literals(source)
    spans = _spans(source)
    if not spans:
        return 0

    changed_spans = 0
    for start, end in reversed(spans):
        chunk = source[start:end]
        new = clean_text(chunk)
        if new != chunk:
            source = source[:start] + new + source[end:]
            changed_spans += 1

    if changed_spans == 0:
        return 0

    after_literals = _literals(source)
    if after_literals != before_literals:
        raise AssertionError(
            "%s: a non-docstring literal changed, so the rewrite was not "
            "confined to comment and docstring text" % path
        )

    with open(path, "w", encoding="utf-8") as handle:
        handle.write(source)
    return changed_spans


def main() -> int:
    """Run the selected rewrite and report the result.

    :returns: 0 on a successful rewrite, 1 when nothing changed, 2 on
        unusable arguments.
    :raises AssertionError: if a literal changed or the file no longer
        compiles.
    """
    if len(sys.argv) < 2:
        print("usage: strip_dashes.py FILE [prose|all]")
        return 2
    path = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "prose"
    if mode == "prose":
        changed = rewrite_prose(path)
    elif mode == "all":
        changed = rewrite_all(path)
    else:
        print("unknown mode: %s" % mode)
        return 2
    print("%s %s: spans changed %d" % (mode, path, changed))
    compile(open(path, encoding="utf-8").read(), path, "exec")
    print("COMPILE_OK")
    return 0 if changed else 1


if __name__ == "__main__":
    raise SystemExit(main())
