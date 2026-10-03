from pathlib import Path
import json
import hashlib
from typing import Any


def canonical_json_bytes(obj: Any) -> bytes:
    """Serialize object to deterministic canonical JSON bytes.
    
    Keys are sorted, whitespace is minimized, NaN/Infinity are rejected,
    and output is UTF-8 encoded.
    """
    json_str = json.dumps(
        obj,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )
    return json_str.encode("utf-8")


def fingerprint_json(path: Path) -> str:
    """Calculate SHA-256 fingerprint of JSON file using canonical bytes."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return hashlib.sha256(canonical_json_bytes(data)).hexdigest()
