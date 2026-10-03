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


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Calculate or verify canonical JSON fingerprint.")
    parser.add_argument("file", type=Path, help="Target JSON file")
    parser.add_argument("--expect", type=str, default=None, help="Expected SHA-256 fingerprint")
    args = parser.parse_args(argv)

    if not args.file.exists():
        print(f"Error: File not found: {args.file}")
        return 1

    try:
        digest = fingerprint_json(args.file)
    except Exception as exc:
        print(f"Error calculating fingerprint: {exc}")
        return 1

    if args.expect:
        if digest == args.expect:
            return 0
        else:
            print(f"Fingerprint mismatch for {args.file}!\nExpected: {args.expect}\nActual:   {digest}")
            return 1

    print(digest)
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(main(sys.argv[1:]))
