"""
SMILE Lexer — Tokenizer for the SMILE (Syntax Memes In Lahori English) language.
Based on the Week 1 specification document.
"""

import re
from dataclasses import dataclass, asdict
from typing import List


@dataclass
class Token:
    """Represents a single token produced by the SMILE lexer."""
    type: str       
    value: str      
    line: int      
    column: int     


TOKEN_SPEC: List[tuple] = [
    # ── Comments (skip) ──
    ("COMMENT",        r"~[^~]*~"),

    # ── String literals ──
    ("STRING",         r'"[^"]*"'),

    # ── Multi-word keywords (must come before single-word) ──
    ("KEYWORD",        r"\bshuru\s+karo\b"),
    ("KEYWORD",        r"\bwarna\s+agar\b"),
    ("KEYWORD",        r"\bjab\s+tak\b"),
    ("KEYWORD",        r"\bbaar\s+baar\b"),
    ("KEYWORD",        r"\bwapas\s+de\b"),
    ("KEYWORD",        r"\bsach\s+jhooth\b"),
    ("KEYWORD",        r"\blo\s+bhi\b"),

    # ── Multi-word operators ──
    ("OPERATOR",       r"\bzyada\s+ya\s+barabar\b"),
    ("OPERATOR",       r"\bkam\s+ya\s+barabar\b"),
    ("OPERATOR",       r"\bna\s+barabar\b"),

    # ── Single-word keywords ──
    ("KEYWORD",        r"\bkhatam\b"),
    ("KEYWORD",        r"\badad\b"),
    ("KEYWORD",        r"\bdesi\b"),
    ("KEYWORD",        r"\bbaat\b"),
    ("KEYWORD",        r"\bkhaali\b"),
    ("KEYWORD",        r"\bagar\b"),
    ("KEYWORD",        r"\bwarna\b"),
    ("KEYWORD",        r"\brok\b"),
    ("KEYWORD",        r"\bagla\b"),
    ("KEYWORD",        r"\bkaam\b"),
    ("KEYWORD",        r"\blo\b"),
    ("KEYWORD",        r"\bbula\b"),
    ("KEYWORD",        r"\bbatao\b"),

    # ── Boolean literals ──
    ("BOOLEAN",        r"\bbilkul\b"),
    ("BOOLEAN",        r"\bnahi\b"),

    # ── Single-word operators ──
    ("OPERATOR",       r"\brakho\b"),
    ("OPERATOR",       r"\bjoro\b"),
    ("OPERATOR",       r"\bghata\b"),
    ("OPERATOR",       r"\bguna\b"),
    ("OPERATOR",       r"\btaqseem\b"),
    ("OPERATOR",       r"\bbacha\b"),
    ("OPERATOR",       r"\bzyada\b"),
    ("OPERATOR",       r"\bkam\b"),
    ("OPERATOR",       r"\bbarabar\b"),
    ("OPERATOR",       r"\baur\b"),
    ("OPERATOR",       r"\bya\b"),
    ("OPERATOR",       r"\bulta\b"),

    # ── Delimiters ──
    ("DELIMITER",      r"\bshuru\b"),
    ("DELIMITER",      r"\bbanda\b"),
    ("DELIMITER",      r"\bbas\b"),

    # ── Number literals (decimal before integer) ──
    ("NUMBER",         r"\b[0-9]+\.[0-9]+\b"),
    ("NUMBER",         r"\b[0-9]+\b"),

    # ── Identifiers ──
    ("IDENTIFIER",     r"\b[a-zA-Z][a-zA-Z0-9_]*\b"),

    # ── Whitespace (skip) ──
    ("SKIP",           r"[ \t\r]+"),

    # ── Newline (track line numbers) ──
    ("NEWLINE",        r"\n"),

    # ── Anything else is an error ──
    ("ERROR",          r"."),
]

# Build a single master regex from the spec
_MASTER_PATTERN = "|".join(
    f"(?P<{name}_{i}>{pattern})" for i, (name, pattern) in enumerate(TOKEN_SPEC)
)
_MASTER_RE = re.compile(_MASTER_PATTERN, re.DOTALL)


def tokenize(source_code: str) -> dict:
    """
    Tokenize SMILE source code.

    Returns a dict with:
      - tokens: list of token dicts
      - errors: list of error dicts
    """
    tokens: List[dict] = []
    errors: List[dict] = []
    line = 1
    line_start = 0

    for match in _MASTER_RE.finditer(source_code):
        kind = match.lastgroup            # e.g. "KEYWORD_3"
        value = match.group()
        col = match.start() - line_start + 1

        # Extract the category name (strip the _N suffix)
        category = kind.rsplit("_", 1)[0]

        if category == "NEWLINE":
            line += 1
            line_start = match.end()
            continue
        elif category == "SKIP":
            continue
        elif category == "COMMENT":
            # Count newlines inside multi-line comments
            newlines_in_comment = value.count("\n")
            if newlines_in_comment:
                line += newlines_in_comment
                line_start = match.end() - (len(value) - value.rfind("\n") - 1)
            continue
        elif category == "ERROR":
            errors.append({
                "message": f"faaaah: line {line} -> '{value}' kya hai bhai? Ye token samajh nahi aaya",
                "line": line,
                "column": col,
                "value": value,
            })
            continue

        # Normalize multi-word token values (collapse whitespace)
        normalized_value = re.sub(r"\s+", " ", value)

        tokens.append(asdict(Token(
            type=category,
            value=normalized_value,
            line=line,
            column=col,
        )))

    return {
        "tokens": tokens,
        "errors": errors,
        "total_tokens": len(tokens),
        "total_errors": len(errors),
    }


# ─── Quick CLI test ───
if __name__ == "__main__":
    sample = """\
~ Program 1: Even ya Odd check karo ~
shuru karo
  adad number rakho 14 bas
  adad baqi rakho number bacha 2 bas
  agar baqi barabar 0 shuru
    batao "Even hai bhai" bas
  banda
  warna shuru
    batao "Odd hai yaar" bas
  banda
khatam
"""
    result = tokenize(sample)
    for tok in result["tokens"]:
        print(f"{tok['type']:12s}  {tok['value']:30s}  (line {tok['line']}, col {tok['column']})")
    for err in result["errors"]:
        print(err["message"])
