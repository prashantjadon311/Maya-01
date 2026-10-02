# Project H V2 / Maya

A lightweight Ubuntu personal AI assistant. Implementation is in progress;
voice, browser control, approvals and executors are not yet available.

Start with [Docs/README_FIRST.md](Docs/README_FIRST.md) for the product contracts
and [Docs/TASKS.md](Docs/TASKS.md) for verified implementation status.

## Development

Python 3.11 or newer:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest -v
```

Tests do not require API credentials or make live provider calls.
