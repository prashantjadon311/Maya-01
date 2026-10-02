"""Shared policy scope normalization; executors must recheck before I/O."""

from pathlib import Path


def canonical_path(value: str) -> Path:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise ValueError("Path must be a nonempty string without NUL")
    # Resolve before collapsing '..': a preceding symlink changes its meaning.
    return Path(value).expanduser().resolve(strict=False)
