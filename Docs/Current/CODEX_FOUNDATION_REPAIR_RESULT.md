# Foundation recovery evidence — 2026-10-03

Starting remote main: `a3270ccba5a836f2348940bbb7423f853e1d97ac`.
Normal main checkout; no worktree or detached HEAD. Existing deletions of
`agent.py` and `fix_tests.py` matched the requested cleanup and were preserved.

## Confirmed root cause and repair

Remote run [37058814155](https://github.com/prashantjadon311/Maya-01/actions/runs/37058814155)
failed before tests: Setuptools discovered `app` and `Docs`. Clean local install
also discovered `env314`. Explicit `app*` discovery with `namespaces=false` and
package markers fixes this without moving the source tree.

Current stable [checkout v7](https://github.com/actions/checkout/releases/tag/v7.0.1)
and [setup-python v7](https://github.com/actions/setup-python/releases/tag/v7.0.0)
were reviewed for this push/pull_request workflow on hosted Ubuntu. They retain
the Node24 runtime. CI now tests Python 3.11 and 3.14 and outside-checkout imports.
Discovery follows the [Setuptools package guide](https://setuptools.pypa.io/en/stable/userguide/package_discovery.html).

## Contract changes

- Config: localhost binding, canonical browser capabilities, trimmed identities,
  positive voice/agent/resource limits and the existing 300 MiB ceiling.
- State: Architecture V2 states, strict booleans, declared-field-only updates.
- Action packs: unique IDs, trimmed labels, shared recursive JSON validation.
- Policy: structural RiskLevel, raise-only hints, explicit preapproval risk/env/
  network fields, destructive command invariants, real cwd/file normalization.
- Approvals: required trusted risk, one SHA-256 primitive, constant-time comparison.
- Tests: replaced duplicate-key/pass-only/generated debris; negative approvals
  validate a complete baseline and mutate exactly one field.
- Removed all five obsolete scripts from Git; corrected README, .env.example,
  developer rule examples, task checkpoint and next-execution handoff.

## Verification before independent review

- Clean Python 3.14.4 environment: `/tmp/maya-recovery-venv`.
- `python -m pip install -e ".[dev]"`: success.
- `python -I` imports of app, actions.schema, core.config and policy.engine from
  `/tmp`: success (no repository cwd/PYTHONPATH leakage).
- Full suite: 270 passed; policy modules: 189 passed.
- `git diff --check`: clean; no tracked `fix_*.py` or `agent.py`.
- Isolated daemon harness RSS: 16.215 MiB. This is not the product cgroup stress gate.

Independent GPT-6 Astra reviewer: no Critical/Important findings in
`a3270cc..95dc287`; independently verified 270 tests, isolated imports,
symlink/parent containment, malformed cwd denial and valid-baseline approval tests.
Remote main `35879a58a6d523ebaa4eaa14b50a33bceaf2e67c` passed
[run 37062130566](https://github.com/prashantjadon311/Maya-01/actions/runs/37062130566):
Python 3.11 and 3.14, installs, isolated imports and full suite all successful.
Foundation gate: PASS. PH-030 started only after this observed success.
PH-040 remains responsible for executor timeout/env/network enforcement and
immediate cwd revalidation. No executor is implemented here.
