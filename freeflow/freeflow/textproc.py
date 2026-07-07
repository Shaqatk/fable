"""Pure-text post-processing pipeline.

Turns a raw Whisper transcript into polished text: strips filler words,
applies spoken layout commands, personal-dictionary replacements, snippet
expansion, and whitespace/casing cleanup. Everything here is pure and
deterministic so it can be unit-tested without audio.
"""

from __future__ import annotations

import re

# Filler tokens removed when remove_fillers is on. Matched case-insensitively
# as whole words, optionally followed by a comma. "like" and "you know" are
# only removed when they appear as clear verbal tics (surrounded by commas),
# since they are common legitimate words.
_SIMPLE_FILLERS = r"(?:um+|uh+|erm+|err|hmm+|mhm|uhm+|ähm|euh)"
_FILLER_RE = re.compile(rf"\b{_SIMPLE_FILLERS}\b[,.]?\s*", re.IGNORECASE)
_TIC_RE = re.compile(r",\s*(?:you know|like|I mean|sort of|kind of)\s*,", re.IGNORECASE)

# Spoken layout commands. Whisper usually transcribes them as literal words.
# A preceding comma is part of the command ("item one, new line item two");
# a preceding period belongs to the prior sentence and must be kept.
_NEW_PARA_RE = re.compile(r"(?:,\s*)?\bnew paragraph\b[,.]?\s*", re.IGNORECASE)
_NEW_LINE_RE = re.compile(r"(?:,\s*)?\bnew line\b[,.]?\s*", re.IGNORECASE)
_BULLET_RE = re.compile(
    r"(?:,\s*)?(?:(?:next|new|another)\s+bullet(?:\s+points?)?|bullet\s+points?)\b[,.]?\s*",
    re.IGNORECASE,
)

_SENTENCE_START_RE = re.compile(r"(^|[.!?]\s+|\n)(•\s+)?([a-z])")


def remove_fillers(text: str) -> str:
    text = _FILLER_RE.sub("", text)
    text = _TIC_RE.sub(",", text)
    return text


def apply_spoken_commands(text: str) -> str:
    text = _NEW_PARA_RE.sub("\n\n", text)
    text = _BULLET_RE.sub("\n• ", text)
    text = _NEW_LINE_RE.sub("\n", text)
    return text


def apply_dictionary(text: str, rules: list[dict]) -> str:
    """Apply personal-dictionary replacements as whole words, case-insensitive."""
    for rule in rules:
        src, dst = rule.get("from", ""), rule.get("to", "")
        if not src or not dst:
            continue
        text = re.sub(rf"\b{re.escape(src)}\b", dst, text, flags=re.IGNORECASE)
    return text


def expand_snippets(text: str, snippets: list[dict]) -> str:
    """If the whole utterance is (or contains only) a snippet trigger, expand it.

    Triggers are matched loosely: case-insensitive, ignoring leading/trailing
    punctuation, and tolerating an "insert" prefix (e.g. "insert my email").
    """
    stripped = text.strip().strip(".!?,").strip().lower()
    bare = re.sub(r"^(insert|paste|add)\s+", "", stripped)
    for snip in snippets:
        trigger = snip.get("trigger", "").strip().lower()
        if trigger and bare == trigger:
            return snip.get("text", text)
    return text


def tidy_whitespace(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" +([,.!?;:])", r"\1", text)   # no space before punctuation
    text = re.sub(r" *\n *", "\n", text)          # trim spaces around newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"([,;:])\1+", r"\1", text)     # collapse doubled punctuation
    text = re.sub(r"^[,.;:]\s*", "", text)        # dangling punctuation at start
    return text.strip()


def capitalize_sentences(text: str) -> str:
    return _SENTENCE_START_RE.sub(
        lambda m: m.group(1) + (m.group(2) or "") + m.group(3).upper(), text
    )


def process(text: str, settings: dict) -> str:
    """Run the full pipeline using a settings dict (see config.DEFAULTS)."""
    if not text:
        return ""
    out = expand_snippets(text, settings.get("snippets", []))
    if out != text:
        return out  # snippet expansion returns stored text verbatim
    if settings.get("remove_fillers", True):
        out = remove_fillers(out)
    if settings.get("spoken_commands", True):
        out = apply_spoken_commands(out)
    out = apply_dictionary(out, settings.get("dictionary", []))
    out = tidy_whitespace(out)
    if settings.get("auto_capitalize", True):
        out = capitalize_sentences(out)
    return out
