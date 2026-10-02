"""Project H Deterministic Action Matcher and Argument Substitution."""

import re
import unicodedata
from typing import Any

# Allowed slot identifier: [A-Za-z_][A-Za-z0-9_]*
SLOT_ID_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
SLOT_PLACEHOLDER_PATTERN = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


def normalize_text(text: str) -> str:
    """Normalize text using NFKC and collapse whitespace, preserving original casing."""
    normalized = unicodedata.normalize("NFKC", text)
    return re.sub(r"\s+", " ", normalized).strip()


def parse_phrase_template(phrase: str) -> tuple[re.Pattern[str], list[str]]:
    """
    Parse a phrase template into a compiled case-insensitive anchored regex
    and an ordered list of declared slot names.

    Raises ValueError on malformed templates:
    - Empty or whitespace-only phrases
    - Phrases exceeding 512 characters
    - Unclosed or stray braces
    - Invalid slot identifiers
    - Adjacent ambiguous slots (e.g. {x}{y})
    - Duplicate slot names within the same phrase
    """
    if not isinstance(phrase, str):
        raise ValueError(f"Phrase template must be a string, got {type(phrase)}")

    if len(phrase) > 512:
        raise ValueError(f"Phrase exceeds maximum length of 512 characters ({len(phrase)} chars)")

    normalized = unicodedata.normalize("NFKC", phrase)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if not normalized:
        raise ValueError("Phrase template must not be empty or whitespace only")

    tokens: list[tuple[str, str]] = []  # ('lit', literal_text) or ('slot', slot_name)
    i = 0
    n = len(normalized)
    seen_slots: set[str] = set()
    slot_order: list[str] = []
    last_token_type: str | None = None

    while i < n:
        if normalized[i] == "{":
            j = normalized.find("}", i + 1)
            if j == -1:
                raise ValueError(f"Unclosed slot in phrase template: '{phrase}'")
            if "{" in normalized[i + 1:j]:
                raise ValueError(f"Nested '{{' in phrase template: '{phrase}'")
            slot_name = normalized[i + 1:j]
            if not SLOT_ID_PATTERN.match(slot_name):
                raise ValueError(f"Invalid slot identifier '{slot_name}' in phrase template: '{phrase}'")
            if last_token_type == "slot":
                raise ValueError(f"Adjacent ambiguous slots in phrase template: '{phrase}'")
            if slot_name in seen_slots:
                raise ValueError(f"Duplicate slot '{slot_name}' in phrase template: '{phrase}'")
            seen_slots.add(slot_name)
            slot_order.append(slot_name)
            tokens.append(("slot", slot_name))
            last_token_type = "slot"
            i = j + 1
        elif normalized[i] == "}":
            raise ValueError(f"Stray '}}' in phrase template: '{phrase}'")
        else:
            next_brace = n
            for k in range(i, n):
                if normalized[k] in ("{", "}"):
                    next_brace = k
                    break
            lit = normalized[i:next_brace]
            tokens.append(("lit", lit))
            last_token_type = "lit"
            i = next_brace

    pattern_parts = ["^"]
    for idx, (ttype, val) in enumerate(tokens):
        if ttype == "lit":
            pattern_parts.append(re.escape(val))
        else:
            # Slot capture: non-greedy if followed by literals, greedy if at end
            is_last = (idx == len(tokens) - 1)
            if is_last:
                pattern_parts.append(f"(?P<{val}>.+)")
            else:
                pattern_parts.append(f"(?P<{val}>.+?)")
    pattern_parts.append("$")

    pattern = re.compile("".join(pattern_parts), re.IGNORECASE)
    return pattern, slot_order


def extract_argument_slots(arguments: Any) -> set[str]:
    """Recursively extract all {slot} placeholders referenced in arguments."""
    slots: set[str] = set()
    if isinstance(arguments, str):
        for m in SLOT_PLACEHOLDER_PATTERN.finditer(arguments):
            slots.add(m.group(1))
    elif isinstance(arguments, dict):
        for v in arguments.values():
            slots.update(extract_argument_slots(v))
    elif isinstance(arguments, list):
        for item in arguments:
            slots.update(extract_argument_slots(item))
    return slots


def substitute_arguments(arguments: Any, captured_slots: dict[str, str]) -> Any:
    """
    Safely replace explicit {slot} placeholders in arguments using captured_slots.
    Preserves data types and original case. Does not use eval, str.format, or format_map.
    """
    if isinstance(arguments, str):
        def repl(match: re.Match[str]) -> str:
            slot_name = match.group(1)
            if slot_name in captured_slots:
                return str(captured_slots[slot_name])
            return match.group(0)

        return SLOT_PLACEHOLDER_PATTERN.sub(repl, arguments)

    if isinstance(arguments, dict):
        return {k: substitute_arguments(v, captured_slots) for k, v in arguments.items()}

    if isinstance(arguments, list):
        return [substitute_arguments(item, captured_slots) for item in arguments]

    return arguments
