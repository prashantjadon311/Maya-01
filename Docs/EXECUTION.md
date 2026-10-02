# Project H — Gemini / Antigravity Execution Contract V2

## 1. Role

You are the implementation engineer. The documents in this directory are the product/architecture authority.

Do not begin by redesigning the project. Begin by reading and inspecting.

## 2. First run

1. Read `SKILL.md`.
2. Read all authority docs in its listed order.
3. Inspect repository tree and git status.
4. Identify existing code worth preserving.
5. Compare it to V2 architecture.
6. Update `TASKS.md` only with factual current state.
7. Start at `CURRENT_TASK`.

## 3. Existing work

Do not delete existing Project H code because V2 changed.

Classify each existing file:
- reuse unchanged;
- adapt;
- superseded;
- unrelated.

Preserve useful code until replacement tests pass.

## 4. TDD

Security/policy/config code requires test-first development.

For GUI/site/manual integrations where unit TDD is limited:
- create protocol/schema tests first;
- create fake adapter;
- define manual acceptance steps;
- record live smoke evidence.

## 5. Live API usage

Default automated tests must not burn hosted API quota.

Use fakes.

Live NVIDIA calls are manual/integration-tagged.

Never print `NVIDIA_API_KEY`.

## 6. Nemotron usage

Project H runtime, not Gemini itself, uses Nemotron.

Gemini may implement/debug the code in Antigravity.

Do not confuse:
- implementation model: Gemini;
- product runtime model: Nemotron.

## 7. Terminal rules during development

Gemini may run normal development commands in the development environment, but the product code it builds must obey Project H's runtime approval model.

Do not weaken product runtime policy because development is trusted.

## 8. Browser extension development

Use Firefox WebExtension APIs and Native Messaging.

Keep permissions minimal.

Do not ship `<all_urls>` as a shortcut to finish faster.

Adapters must fail clearly when page structure is no longer recognized.

## 9. Memory workflow

After every new resident dependency/subsystem:
1. measure daemon RSS;
2. record delta;
3. compare to budget;
4. investigate surprising growth immediately.

Do not wait until the last task to discover that one inference library ate the budget.

## 10. UI workflow

Implement `UI.md`, not the old reference image literally.

Use the image only as visual inspiration.

The central visual is an original SVG AI Core.

Do not introduce:
- React;
- npm build chain;
- icon mega-library;
- animation framework;
- chart library;
- remote background media.

## 11. Approval workflow

Before wiring real execution:
- test policy using fake executor;
- test approval with fake popup;
- test action hash;
- then connect real process/files.

## 12. Coding agent workflow

Implement one logical agent first.

Goal:
`plan -> tool -> policy -> action -> observe -> verify -> finish`

Do not build multi-agent delegation until one agent is safe and measurable.

If multi-agent is later enabled, keep concurrency 1 by default and logical tasks in one process.

## 13. Result packet per task

```text
TASK:
STATUS:
FILES CHANGED:
TESTS ADDED:
COMMANDS RUN:
RESULT:
NEGATIVE/SECURITY TEST:
RSS BEFORE:
RSS AFTER:
KNOWN LIMITATIONS:
NEXT TASK:
```

## 14. Final result packet

Must include objective evidence:
- pytest totals;
- failed/skipped tests;
- live integration checks;
- systemd unit status;
- memory stress peak;
- browser extension permissions;
- voice pre-wake network assertion;
- security red-team summary;
- clean install test.

No "should work" completion language.
