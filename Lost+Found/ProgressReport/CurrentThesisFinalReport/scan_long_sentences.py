#!/usr/bin/env python3
r"""Scan thesis chapter sources for prose sentences longer than 45 words.

AXIOMS: Goal rev 3 requires readability audits every cycle, and overlong
sentences are a readability defect. Frozen constructs (captions, AccSupp
alt-text) are excluded because they are already handled by caption short
forms and are not prose. Comments carry no rendered text.

THEORIES: Strip comments, caption/AccSupp blocks, heading/paragraph titles,
float/table/algorithm environments, and display-math environments (all
non-prose or frozen), turn \par into a sentence boundary, keep only the
first argument of \texorpdfstring, split remaining prose on
sentence-ending punctuation, then count space-delimited word tokens
containing at least one alphanumeric char.

APPLICATIONS: Run from the thesis directory with system python3:
    python3 scan_long_sentences.py
Exit code 0 always (report-only tool; no edits are made).

CITATIONS: Sentence-length threshold of 45 words follows the readability
criterion used throughout this audit session (goal revision 3).
"""
import re
from pathlib import Path

FILES = [
    "chapter_01_introduction.tex",
    "chapter_02_literature_review.tex",
    "chapter_03_methodology.tex",
    "chapter_04_results.tex",
    "chapter_05_conclusion.tex",
    "abstract.tex",
    "appendix.tex",
]
LIMIT = 45


def strip_frozen(text: str) -> str:
    """Remove comments, caption bodies, and AccSupp blocks from source text.

    Parameters
    ----------
    text : str
        Raw .tex file content.

    Returns
    -------
    str
        Source with non-prose constructs blanked out (newlines preserved so
        reported line numbers stay accurate).

    Exceptions
    ----------
    None; regex-only transformation.
    """
    text = re.sub(r"(?<!\\)%.*", "", text)

    def keep_lines(match: "re.Match[str]") -> str:
        """Replace a frozen block with a sentence terminator plus padding.

        Parameters
        ----------
        match : re.Match[str]
            The matched caption or AccSupp block.

        Returns
        -------
        str
            "." followed by the block's newline count so the preceding
            prose sentence ends at the block boundary while downstream
            line numbers stay aligned to raw source.
        """
        return "." + "\n" * match.group(0).count("\n")

    text = re.sub(r"\\BeginAccSupp.*?\\EndAccSupp", keep_lines, text, flags=re.S)
    text = re.sub(r"\\caption(?:\[[^\]]*\])?\{(?:[^{}]|\{[^{}]*\})*\}", keep_lines, text)
    # Float and table environments are frozen structure: blank them whole so
    # table rows and row remnants cannot masquerade as prose sentences.
    text = re.sub(
        r"\\begin\{(table|figure|longtable|algorithm)\}(?:\[[^\]]*\])?"
        r".*?\\end\{\1\}",
        keep_lines,
        text,
        flags=re.S,
    )
    text = re.sub(
        r"\\begin\{tabularx?\}(?:\[[^\]]*\])?\{(?:[^{}]|\{[^{}]*\})*\}"
        r".*?\\end\{tabularx?\}",
        keep_lines,
        text,
        flags=re.S,
    )
    # Display math envs: a prose lead-in like "yield \begin{equation}..." has
    # no internal period, so the equation and trailing text merge into the
    # sentence. Blank the env (outer math delimiters stay in the prose).
    text = re.sub(
        r"\\begin\{(equation\*?|align\*?|gather\*?|multline\*?|eqnarray\*?)\}"
        r"(?:\[[^\]]*\])?.*?\\end\{\1\}",
        keep_lines,
        text,
        flags=re.S,
    )
    # Heading titles would otherwise swallow the sentence's first words;
    # blank the title, leaving surrounding prose intact.
    text = re.sub(
        r"\\(?:chapter|section|subsection|subsubsection|paragraph|subparagraph)\*?"
        r"\{(?:[^{}]|\{[^{}]*\})*\}",
        keep_lines,
        text,
    )
    # \texorpdfstring{printable}{pdf} keeps only the printable argument.
    for _ in range(10):
        new = re.sub(
            r"\\texorpdfstring\{((?:[^{}]|\{[^{}]*\})*?)\}"
            r"\{(?:[^{}]|\{[^{}]*\})*\}",
            r"\1",
            text,
        )
        if new == text:
            break
        text = new
    # Terminate sentences at remaining environment boundaries (itemize,
    # enumerate, unblanked blocks) and drop frozen labels.
    text = re.sub(r"\\end\{[a-zA-Z*]+\}", lambda m: m.group(0) + ".", text)
    text = re.sub(r"\\begin\{[a-zA-Z*]+\}", lambda m: m.group(0) + ".", text)
    # Each \item starts its own prose unit; without this, period-less items
    # merge into one giant false-positive sentence.
    text = re.sub(r"\\item\b", lambda m: "." + m.group(0), text)
    text = re.sub(r"\\label\{[^}]*\}", "", text)
    # \par is a paragraph break: treat it as a sentence terminator.
    text = re.sub(r"\\par\b", ".", text)
    return text


def count_words(sentence: str) -> int:
    """Count space-delimited tokens that contain at least one alphanumeric.

    Parameters
    ----------
    sentence : str
        Candidate sentence text.

    Returns
    -------
    int
        Word count (math/commands inflate this slightly, which is flagged
        in the report header as a known upper-bound bias).
    """
    return sum(1 for tok in sentence.split() if re.search(r"[A-Za-z0-9]", tok))


def main() -> int:
    """Scan all FILES and print every sentence over LIMIT words.

    Returns
    -------
    int
        Always 0 (report-only).
    """
    hits = 0
    for name in FILES:
        path = Path(name)
        if not path.exists():
            continue
        raw = path.read_text(encoding="utf-8")
        clean = strip_frozen(raw)
        # Protect decimal points so "1.605054" does not split sentences.
        clean = re.sub(r"(?<=\d)\.(?=\d)", "@DOT@", clean)
        for m in re.finditer(r"[^.!?]+(?:[.!?]+|$)", clean):
            sent = m.group(0)
            if not re.search(r"[A-Za-z0-9]", sent):
                continue
            line_no = clean.count("\n", 0, m.start()) + 1
            n = count_words(sent)
            if n > LIMIT:
                flat = " ".join(sent.split()).replace("@DOT@", ".")
                print(f"{name}:{line_no}: {n}w :: {flat[:140]}")
                hits += 1
    print(f"total overlong sentences: {hits}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
