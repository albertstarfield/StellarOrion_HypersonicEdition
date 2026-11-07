# Copyright (c) 2026 Wahyu Suryo Samudro. All rights reserved.
# SPDX-License-Identifier: MIT
# The line below is a CrossHair directive, not commented out code.
# ruff: file-ignore[commented-out-code]
# crosshair: analysis_kind=PEP316
"""Pure, side-effect-free helpers for the Week 17 narrative scaffold.

WHY THIS EXISTS
    The generator in ``make_pptx.py`` is orchestration: it opens files, talks to
    the EasyPPTX writer and writes a package.  Every decision that can be
    decided by pure logic, however, belongs here, in a module with no imports
    beyond the standard library.  Two reasons.

    1.  TESTABILITY.  A pure function can be checked by symbolic execution
        (CrossHair) without a filesystem, a PowerPoint installation or a
        network.  The checks in this file are contracts, not comments.

    2.  VERIFIABILITY.  This module carries the CrossHair directive
        ``# crosshair: analysis_kind=PEP316`` in its first line, so
        ``crosshair check scaffold_logic.py`` explores the functions that
        declare contracts and reports a counterexample when a contract can be
        broken.  The generator module itself has no contract-bearing function
        because every one of its functions performs I/O.

THEORIES
    1.  A contract that holds for every admissible input is a property of the
        function, not of the run.  Therefore it is checked symbolically, once,
        instead of by sampling.
    2.  Normalisation is idempotent: normalising an already normalised string
        yields the same string.  This is what lets the update mode compare a
        visible slot against the recorded body without being confused by
        line breaks.
    3.  Escaping is injective on the metacharacters: the escaped text never
        contains a raw ``<`` or ``>``, so an XML consumer can never read the
        escaped value as markup.

APPLICATIONS
    ``make_pptx.py`` imports :func:`collapse_whitespace`, :func:`escape_xml`,
    :func:`is_hex_colour`, :func:`require_text`, :func:`require_mapping` and
    :func:`identity_text` from this module and never defines its own copy.

CITATIONS
    * CrossHair 0.0.111 -- https://github.com/Quantumthought/crosshair
    * PEP 316 -- https://peps.python.org/pep-316/ (docstring contracts)
    * W3C XML 1.0 -- https://www.w3.org/TR/xml/ (the five metacharacters)
"""

from __future__ import annotations

import re
import string

#: The number of hexadecimal digits in a colour literal.
HEX_COLOUR_LENGTH = 6

HEX_COLOUR_PATTERN = re.compile(r"\A[0-9A-Fa-f]{6}\Z")


class ScaffoldError(RuntimeError):
    """Raised when the scaffold specification or the deck violates an invariant.

    Args:
        message: The description of what went wrong.
    """


def collapse_whitespace(text: str) -> str:
    """Fold every run of whitespace into a single space and strip the ends.

    The function is idempotent: collapsing an already collapsed string returns
    the same string.  The generator relies on that property when it compares a
    slot body on the slide with the body recorded in the speaker notes.

    Args:
        text: The text to normalise.

    Returns:
        The normalised text.

    post: len(_) <= len(text)
    post: "  " not in _
    post: _ == " ".join(text.split())
    """
    return " ".join(text.split())


def escape_xml(text: str) -> str:
    """Escape the four characters that may not appear literally in an XML attribute.

    The ampersand is replaced first, so an ampersand that is introduced by a
    later replacement is escaped as well.  The apostrophe is deliberately left
    alone, because a double quoted attribute value may hold one.

    Args:
        text: The text to escape.

    Returns:
        The escaped text.

    post: "<" not in _
    post: ">" not in _
    post: len(_) >= len(text)
    """
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def is_hex_colour(text: str) -> bool:
    """Report whether the text is exactly six hexadecimal digits.

    Args:
        text: The candidate colour.

    Returns:
        True when the text is a six digit hexadecimal colour.

    post: not _ or len(text) == 6
    """
    if len(text) != HEX_COLOUR_LENGTH:
        return False
    return all(character in string.hexdigits for character in text)


def require_text(value: object, what: str) -> str:
    """Return the stripped text, or fail loudly.

    The function never returns an empty string and never returns a value that
    is not text, because every field that reaches the deck must carry meaning.

    Args:
        value: The candidate value.
        what: The name of the value, used in the failure message.

    Returns:
        The stripped text.

    Raises:
        ScaffoldError: When the value is not a string or is blank.

    pre: isinstance(value, str) and len(value.strip()) > 0
    post: len(_) > 0
    """
    if not isinstance(value, str):
        failure = f"the specification needs {what} to be a string, found {type(value).__name__}"
        raise ScaffoldError(failure)
    stripped = value.strip()
    if len(stripped) == 0:
        failure = f"the specification needs {what} to be a non-empty string"
        raise ScaffoldError(failure)
    return stripped


def require_mapping(value: object, what: str) -> dict[str, object]:
    """Return the value as a mapping, or fail loudly.

    Args:
        value: The candidate value.
        what: The name of the value, used in the failure message.

    Returns:
        The mapping.

    Raises:
        ScaffoldError: When the value is not a JSON object.

    pre: isinstance(value, dict)
    """
    if not isinstance(value, dict):
        failure = f"the specification needs {what} to be a JSON object, found {type(value).__name__}"
        raise ScaffoldError(failure)
    return value


def identity_text(raw: dict[str, object], key: str) -> str:
    """Return the stripped text of one identity field.

    A field that is absent reads as an empty string; the caller decides
    whether an empty identity field is fatal.

    Args:
        raw: The identity object.
        key: The name of the field.

    Returns:
        The stripped text of the field, or an empty string.
    """
    value = raw.get(key)
    if value is None:
        return ""
    return str(value).strip()
