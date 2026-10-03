TASK MODE:
MAYA / PROJECT H — ONE-SHOT PH-050→PH-180 COOKBOOK GENERATION EXECUTION

MODEL:
Gemini 3.6 High (Thinking)

ROLE:
Principal Software Architect
Principal Python Engineer
Security Architect
Test Architect
Implementation-Spec Compiler

REPOSITORY:
https://github.com/prashantjadon311/Maya-01

THIS IS A SINGLE-RUN EXECUTION TASK.

Do not merely review the design.
Do not return a plan instead of executing it.
Do not implement PH-050 production code.
Do not implement any PH-060→PH-180 production code.

Your only deliverable is the complete, validated, frozen implementation cookbook
defined by the two canonical files already present in the repository.

======================================================================
0. CANONICAL INPUT FILES
======================================================================

Read FIRST, in this order:

1.
Docs/ImplementationCookbook/MAYA_IMPLEMENTATION_COMPILER_V3_DESIGN.md

2.
Docs/ImplementationCookbook/2026-10-03-maya-cookbook-generation.md

Treat:

MAYA_IMPLEMENTATION_COMPILER_V3_DESIGN.md
as the approved SPEC.

Treat:

2026-10-03-maya-cookbook-generation.md
as the approved EXECUTION PLAN.

If the plan conflicts with the design spec:

DESIGN SPEC WINS.

Do not redesign the methodology.

======================================================================
1. IMPORTANT SHA RULING
======================================================================

Current remote main is expected to be:

d603173624ddc9285b32ee00f33c10be2ecc9b58

Its parent is:

ef00714c86d3d7b5684d693da35aa82595a088d4

The only changes between these commits are the two cookbook design/plan files.

Therefore use TWO explicit baselines:

COOKBOOK_WORK_BASE_SHA:
d603173624ddc9285b32ee00f33c10be2ecc9b58

PRODUCT_CODE_BASE_SHA:
ef00714c86d3d7b5684d693da35aa82595a088d4

Reason:

- d603... is the snapshot from which cookbook generation work begins.
- ef007... is the last production-code state before cookbook documents were added.
- cookbook analysis of existing PH-000→PH-040 production code should identify
  ef007... as the production baseline.
- repository/worktree/branch operations begin from d603....

This is an intentional ruling that supersedes the older plan assertion that
`base_sha` alone must equal ef007....

The generated freeze manifest MUST preserve both values.

Do not silently collapse them into one ambiguous field.

======================================================================
2. PRE-FLIGHT
======================================================================

Run:

git status --short
git branch --show-current
git fetch origin
git checkout main
git pull --ff-only origin main
git rev-parse HEAD
git log -3 --oneline

Expected current HEAD:

d603173624ddc9285b32ee00f33c10be2ecc9b58

If main has moved:

inspect ALL commits since d603....

If changes are only cookbook documentation:
record a ruling and continue from latest main.

If production code changed:
perform a delta analysis before continuing.

Do NOT reset or destroy local changes.

If working tree is dirty with unrelated user work:
create an isolated worktree from remote main without touching those changes.

======================================================================
3. ISOLATED WORKSPACE
======================================================================

Do NOT perform cookbook generation directly on main.

Preferred worktree:

../Maya-cookbook-generation

Preferred branch:

cookbook-generation

If branch/worktree already exists:

inspect it.

If it contains a valid progress ledger for THIS exact plan:
resume.

Otherwise fail safely rather than overwrite unrelated work.

Preferred commands when clean and branch absent:

git worktree add ../Maya-cookbook-generation \
  -b cookbook-generation \
  origin/main

cd ../Maya-cookbook-generation

Never:

git reset --hard over user work
git clean -fdx on user workspace
git push --force
git push --force-with-lease

======================================================================
4. DURABLE EXECUTION LEDGER
======================================================================

Create OUTSIDE tracked cookbook artifacts, in a git-ignored local path:

.superpowers/sdd/2026-10-03-maya-cookbook-generation/progress.md

If `.superpowers/` is not already ignored:

DO NOT casually modify product .gitignore merely for convenience.

Instead use an external temporary/local state directory, for example:

~/.local/state/maya-cookbook-generation/progress.md

The ledger must begin:

# Cookbook generation ledger

Then record:

PLAN:
Docs/ImplementationCookbook/2026-10-03-maya-cookbook-generation.md

SPEC:
Docs/ImplementationCookbook/MAYA_IMPLEMENTATION_COMPILER_V3_DESIGN.md

COOKBOOK_WORK_BASE_SHA:
...

PRODUCT_CODE_BASE_SHA:
...

For every task:

Task N: STARTED
Task N: Ruling: ...
Task N: COMPLETE
Commit:
Tests:
Artifacts:
Open findings:

This ledger must never contain secrets or huge chat transcripts.

======================================================================
5. EXECUTION RULE
======================================================================

Execute ALL 16 tasks from:

Docs/ImplementationCookbook/2026-10-03-maya-cookbook-generation.md

in exact task order.

DO NOT stop after Task 1.
DO NOT ask me to send another prompt between tasks.
DO NOT merely create empty placeholder files.

Continue autonomously until:

A. cookbook reaches FROZEN state;

or

B. one of the explicit hard-stop conditions in the approved design/plan occurs.

Ordinary implementation problems are NOT stop conditions.

Fix them.

======================================================================
6. TDD FOR COOKBOOK TOOLING
======================================================================

For actual executable tooling under:

tools/cookbook/

follow strict TDD.

For each behavior:

1. write failing test;
2. run it;
3. confirm it fails for the intended missing behavior;
4. implement minimal code;
5. run focused test;
6. run relevant regression.

Do not write validator/inventory production code first.

Required tooling includes the plan-defined:

tools/cookbook/__init__.py
tools/cookbook/model.py
tools/cookbook/inventory.py
tools/cookbook/validate.py
tools/cookbook/fingerprint.py

and their tests.

Documentation itself does not need artificial RED tests before prose creation,
but machine-manifest contracts MUST be validated.

======================================================================
7. PYDANTIC V2 RULE FOR MACHINE MODELS
======================================================================

The current project uses Pydantic v2.

For security/contract-sensitive cookbook manifest models prefer:

model_config = ConfigDict(
    strict=True,
    extra="forbid",
)

unless an exact model has a documented reason not to.

Important:

ConfigDict(frozen=True)

prevents attribute reassignment but DOES NOT deep-freeze nested dict/list
objects.

Therefore do not use:

frozen=True

as proof that nested machine manifests are immutable.

For immutable contract data prefer immutable nested types where appropriate:

tuple
frozenset

or defensive copies at boundaries.

Do not introduce a new third-party dependency merely for deep immutability.

======================================================================
8. DO NOT MODIFY MAYA PRODUCTION CODE
======================================================================

During cookbook generation:

DO NOT modify:

app/

except if an unavoidable concrete cookbook-blocking defect is discovered.

Even then:

DO NOT FIX THE PRODUCTION DEFECT IN THIS TASK.

Instead:

record:

CURRENT_CODE_DEFECT-xxx

with:

file
symbol
impact
affected future phases
required future repair phase

The cookbook task is a design/specification compiler, not a stealth PH-050
implementation.

Do not modify current runtime behavior.

======================================================================
9. AUTHORITY INGESTION
======================================================================

Read:

Docs/SKILL.md

Then authority order exactly:

Docs/DOCS.md
Docs/SECURITY.md
Docs/ARCHITECTURE.md
Docs/CONFIG.md
Docs/UI.md
Docs/PLAN.md
Docs/TASKS.md
Docs/EXECUTION.md

Important distinction:

BEHAVIORAL AUTHORITY:
use the authority precedence above.

ACTUAL IMPLEMENTATION STATE:
determine using:

git tree
source code
tests
CI
merged commits

before stale task-ledger prose.

Do not silently rewrite higher authority to make current code look correct.

======================================================================
10. CURRENT CODE REVERSE ENGINEERING
======================================================================

Deeply inspect all currently relevant PH-000→PH-040 production code.

At minimum inspect:

app/core/
app/actions/
app/policy/
app/executors/
app/browser/

plus:

pyproject.toml
config example
action/preapproval examples
CI workflow
all current tests

Create the full current-code model required by the plan.

Do not rely only on AST extraction.

AST inventory is an accelerator.

You must manually analyze:

state ownership
trust boundaries
security roles
side effects
resource ownership
call relationships
current invariants
future extension points

Classify every relevant existing symbol:

KEEP
EXTEND
REFACTOR_IN_PLACE
REPLACE_LATER
DEPRECATED
DO_NOT_TOUCH

======================================================================
11. REQUIREMENT COMPILATION
======================================================================

Convert authority prose into atomic requirement IDs.

Every requirement must eventually map:

requirement
→ owning phase
→ file
→ symbol/function
→ test
→ acceptance evidence

Do not use giant combined requirements such as:

"browser must be secure"

Split meaningful properties.

Example categories:

voice privacy
policy
approval
files
processes
browser
provider
agent
storage
dashboard
tray
memory
packaging
acceptance

Every requirement gets one stable ID.

======================================================================
12. FINAL SYSTEM FIRST
======================================================================

Before writing phase packets:

design/freeze the FINAL PH-180 Maya system.

Then slice it into PH-050→PH-180.

Do not let each phase independently invent architecture.

Explicitly freeze:

component graph
dependency direction
composition root
shared objects
object lifetimes
shutdown order
state ownership
trust boundaries
public interfaces
internal schemas
state machines
concurrency
timeouts
retries
idempotency
error taxonomy
resource bounds
privacy/retention

======================================================================
13. FRESHER STANDARD
======================================================================

Assume the eventual implementation engineer:

- knows Python syntax;
- can translate exact logic into code;
- does NOT safely know architecture;
- does NOT safely choose algorithms;
- does NOT safely design concurrency;
- does NOT safely reason about security;
- does NOT know where code belongs.

Therefore every non-trivial implementation instruction MUST specify:

FILE
SYMBOL
PURPOSE
SIGNATURE
CALLED_BY
CALLS
INPUT TYPES
TRUST LEVEL
PRECONDITIONS
ALGORITHM
OUTPUT
POSTCONDITIONS
SIDE EFFECTS
STATE MUTATION
ASYNC MODEL
LOCKING
TIMEOUT
CANCELLATION
RETRY
IDEMPOTENCY
ERRORS
SECURITY INVARIANTS
RESOURCE BOUNDS
CLEANUP
AUDIT
REFERENCE CODE
UNIT TESTS
NEGATIVE TESTS
DO NOT

If the fresher could make two materially different architectural choices:

the cookbook is not detailed enough.

======================================================================
14. REFERENCE CODE TARGET
======================================================================

The cookbook is intentionally more code-heavy than normal architecture docs.

Tier A:
70–95% implementation-ready reference code for:

approval broker
single-use grant/hash binding
provider adapter parsing
router
agent runtime
voice state machine
bounded audio/buffers
authenticated local IPC/native protocol
storage transaction patterns
lifecycle/composition root
security helpers
resource-bound helpers

Tier B:
exact interfaces + detailed algorithms + critical branches for:

FastAPI
tray
repository/developer services
config CRUD

Tier C:
exact structure/contracts for:

HTML
CSS
basic vanilla JS
packaging metadata

Do not write thousands of obvious UI lines just to increase page count.

The objective is:

MINIMIZE FUTURE CODER REASONING TOKENS

without creating a duplicate full source tree inside documentation.

======================================================================
15. EXTERNAL API RESEARCH
======================================================================

Use Context7/current authoritative docs for implementation-sensitive APIs.

At the time each relevant contract is frozen, verify CURRENT APIs for:

Pydantic v2
FastAPI
OpenAI Python AsyncOpenAI
NVIDIA OpenAI-compatible endpoint usage
openWakeWord
Firefox WebExtension
Firefox Native Messaging
systemd user service
MemoryHigh / MemoryMax
D-Bus / StatusNotifierItem implementation path
SQLite API/layer selected
Python asyncio/subprocess/path APIs

Do not rely on memory.

Record in cookbook:

source
verification date
version where known
exact API used
affected phase(s)

If Context7 lacks an integration-specific detail:

use official upstream documentation.

Do not use random blogs when official docs exist.

======================================================================
16. NVIDIA PROVIDER CONTRACT
======================================================================

PH-060 MUST be frozen against CURRENT supported OpenAI Python behavior.

The current design intent remains:

one reusable AsyncOpenAI client
custom base URL
explicit timeout
max_retries=0
async cleanup
streaming
tool/function calls
provider-specific objects do not escape adapter
raw reasoning traces are not exposed/persisted by default

Do NOT make live paid/provider API calls in default tests.

Use fakes/transport doubles.

======================================================================
17. RESOURCE CONTRACT
======================================================================

Hard system target remains:

MemoryHigh=240M
MemoryMax=300M

Do not turn design estimates into measured claims.

Mark every resource number as:

FROZEN_LIMIT
ESTIMATED_BUDGET
MEASURED_VALUE

as appropriate.

For every:

queue
deque
dict cache
audio buffer
transcript
model context
provider output
subprocess output
DOM extraction
audit retention
agent step list

define:

hard maximum
enforcement location
behavior on limit
resident/lazy/ephemeral classification

No unbounded structures.

======================================================================
18. SECURITY REVIEW STANDARD
======================================================================

Assume hostile:

model output
action packs
config
browser DOM/text
native messages
provider responses
file paths
symlinks
subprocess output
popup responses
persisted SQLite rows

For every security invariant define:

PRIMARY ENFORCEMENT
DEFENSE IN DEPTH
NEGATIVE TEST
FAILURE MODE

Security must not depend on model prompt compliance.

======================================================================
19. SECURITY TEST PROOF STANDARD
======================================================================

A test name is not evidence.

If a test is called:

test_symlink_swap_is_denied

the fixture must actually create/simulate the swap.

If called:

test_origin_mismatch_denied

it must produce a real mismatching origin.

If called:

test_secret_not_audited

inject a recognizable fake secret and assert it does not appear.

For each security test record:

ATTACK_SETUP
ACTION
EXPECTED_DENIAL
ASSERT_NOT
CLEANUP

======================================================================
20. PHASE PACKETS
======================================================================

Generate:

Docs/ImplementationCookbook/phases/PH050.md
...
Docs/ImplementationCookbook/phases/PH180.md

Each MUST contain all 36 sections required by the approved design.

No:

TBD
TODO
FIXME
"handle appropriately"
"validate properly"
"implement securely"
"as needed"

without immediately defining exact mechanics.

======================================================================
21. TOKEN EFFICIENCY
======================================================================

The MASTER cookbook can be detailed.

But future implementation execution must be phase-local.

For every phase build:

machine/phase_manifest.json

with exact:

required files to read
required interface sections
required capsules
files to create
files to modify
files forbidden to modify
tests
acceptance
output interfaces
stop conditions

The future coding model must NOT need to reread:

all authority docs
all prior phases
full history
old review reports

for every phase.

======================================================================
22. MACHINE VALIDATOR
======================================================================

Implement the validator defined in the plan.

It must mechanically detect at least:

duplicate requirement ID
unmapped requirement
acceptance without test
duplicate/conflicting public interface
future file without owner
illegal dependency direction
dependency cycle
resource without bound
security invariant without negative test
undefined symbol reference
duplicate test ID
phase manifest missing required fields
nonzero mandatory freeze counters while status=FROZEN

Validator output must be deterministic.

Use canonical JSON for fingerprints.

======================================================================
23. PHASE-BY-PHASE GIT
======================================================================

Follow the approved plan's task commits.

Do not wait until the end for one huge commit.

Each task should have:

focused change
tests
validation
commit

Before each commit:

git diff --check

Do not push every tiny internal step.

Push branch after coherent task commits exist.

======================================================================
24. TESTING
======================================================================

For cookbook tooling run focused tests during development.

Before final freeze run:

pytest tests/test_cookbook_inventory.py \
       tests/test_cookbook_validation.py -v

Then FULL existing Maya regression:

pytest -v

Then:

python -m pip install -e ".[dev]"

Run relevant installed imports from outside checkout.

Then:

git diff --check

Do not claim success from test count alone.

Read failures/warnings.

======================================================================
25. FOUR FINAL REVIEW PASSES
======================================================================

After the complete cookbook draft:

PASS A — ARCHITECTURE

Check:

placement
dependency direction
composition
state ownership
lifetimes
undefined interfaces
duplicate responsibility
wrong phase ownership

PASS B — SECURITY

Check:

authorization
forged trust
TOCTOU
IPC auth
secret leaks
browser bypass
voice privacy
agent self-escalation
fail-open behavior
resource exhaustion

PASS C — FRESHER IMPLEMENTABILITY

For every phase ask:

Could a developer who knows syntax but no architecture/algorithm reasoning
implement this without guessing?

If YES:
PASS.

If any design choice remains:
repair cookbook.

PASS D — TOKEN EFFICIENCY

Remove:

repeated rationale
duplicated contracts
historical narrative
repeated code

Do NOT remove:

signatures
algorithms
bounds
security invariants
tests
file placement
lifetimes
stop conditions

======================================================================
26. FORWARD SIMULATION
======================================================================

Trace exact declared symbols for at least:

1.
text deterministic action
→ router
→ registry
→ policy
→ dispatcher
→ executor
→ audit

2.
AI proposed action
→ policy ASK_USER
→ popup
→ single-use grant
→ unchanged hash
→ executor

3.
coding agent
→ provider
→ tool proposal
→ dispatcher
→ file/process
→ verify
→ bounded finish

4.
always listening
→ local wake only
→ command capture
→ STT
→ router

5.
browser
→ daemon policy
→ authenticated local bridge
→ Firefox host permission
→ current-origin check
→ adapter

6.
daemon restart while approval pending
→ pending grant invalidated
→ no execution

7.
NVIDIA unavailable
→ deterministic actions remain operational

8.
dashboard config update
→ validated write
→ transactional reload
→ safe active state

Every arrow must map to actual file/symbol/interface.

======================================================================
27. REVERSE TRACEABILITY
======================================================================

Start from PH-180 acceptance.

Every final behavior must trace:

acceptance evidence
→ test
→ implementation symbol
→ public/internal interface
→ owning phase
→ atomic requirement
→ authority source

Broken chain:

COOKBOOK BLOCKED.

======================================================================
28. FREEZE COUNTERS
======================================================================

Cookbook cannot be FROZEN unless exactly:

UNMAPPED_REQUIREMENTS = 0
UNTESTED_ACCEPTANCE_CRITERIA = 0
UNRESOLVED_PUBLIC_INTERFACES = 0
UNRESOLVED_SECURITY_INTERFACES = 0
UNOWNED_FUTURE_FILES = 0
CIRCULAR_DEPENDENCIES = 0
UNBOUNDED_RESIDENT_STRUCTURES = 0
CRITICAL_GAPS = 0
IMPORTANT_GAPS = 0
GUESS_REQUIRED_IMPLEMENTATION_ITEMS = 0

Do not massage counters.

If a real gap exists:

STATUS = BLOCKED

and identify exact IDs.

======================================================================
29. FINAL FINGERPRINTS
======================================================================

Generate canonical SHA-256 fingerprints for:

interfaces
requirements
phase manifest

Record:

COOKBOOK_VERSION
COOKBOOK_WORK_BASE_SHA
PRODUCT_CODE_BASE_SHA
INTERFACE_HASH
REQUIREMENT_MAP_HASH
PHASE_MANIFEST_HASH

======================================================================
30. MASTER EXECUTION PROMPT
======================================================================

One final deliverable is:

Docs/ImplementationCookbook/execution/MASTER_EXECUTION_PROMPT.md

This prompt will later implement Maya PH-050→PH-180.

It MUST:

- execute one phase packet at a time;
- use phase_manifest for minimal reads;
- perform delta check before each phase;
- use TDD;
- run review and regression gates;
- checkpoint after every phase;
- compact/discard irrelevant previous phase context;
- stop on security/authority/interface/memory blockers;
- never silently redesign architecture;
- never auto-advance through a failed gate.

DO NOT execute this master prompt now.

Generating it is part of cookbook generation.

======================================================================
31. TASKS.md
======================================================================

Do not use stale `Docs/TASKS.md` checkpoint text as factual Git history.

Do not advance CURRENT_TASK to PH-050 implementation merely because cookbook
generation completes.

If you update TASKS.md at all, only record factual cookbook state.

Preferred:
leave production task sequencing unchanged unless explicitly required by the
approved cookbook plan.

======================================================================
32. PUSH + PR
======================================================================

After all 16 cookbook-generation plan tasks complete and all validation passes:

git status --short
git diff --check
pytest -v

Push:

git push -u origin cookbook-generation

Create PR:

base: main
head: cookbook-generation

Title:

Maya: Freeze PH-050 through PH-180 Implementation Cookbook

PR body must contain:

- COOKBOOK_WORK_BASE_SHA
- PRODUCT_CODE_BASE_SHA
- number of atomic requirements
- number of public interfaces
- number of phase packets
- validator test results
- full Maya regression results
- architecture review result
- security review result
- fresher review result
- token-efficiency review result
- all freeze counters
- fingerprints
- known limitations

DO NOT MERGE.

Stop with PR awaiting independent review.

======================================================================
33. HARD STOP CONDITIONS
======================================================================

STOP only for:

1. destructive/irreversible operation required;
2. production-code architectural conflict with no safe resolution;
3. current external API cannot be verified and the interface would be guesswork;
4. security-critical design has multiple incompatible choices not resolved by authority;
5. baseline/full tests fail from an unexplained pre-existing defect;
6. cookbook validator reveals a gap that cannot be resolved from existing authority/code;
7. repository unexpectedly diverges in production code during execution.

Do NOT stop for:

syntax errors
ordinary test failures
missing directories
expected RED tests
small implementation bugs
documentation formatting
simple merge-free branch setup

Fix those yourself.

======================================================================
34. FINAL RESPONSE
======================================================================

Return ONLY a concise result packet:

MAYA COOKBOOK GENERATION:
FROZEN / BLOCKED

COOKBOOK_WORK_BASE_SHA:
PRODUCT_CODE_BASE_SHA:
BRANCH:
HEAD:
PR:

TASKS COMPLETED:
16/16 or exact count

ATOMIC REQUIREMENTS:
MAPPED:
UNMAPPED:

PUBLIC INTERFACES:
UNRESOLVED:

PHASE PACKETS:
PH-050 → PH-180 COMPLETE / INCOMPLETE

REFERENCE CODE CAPSULES:
TEST RECIPES:
MACHINE VALIDATOR:

ARCHITECTURE REVIEW:
SECURITY REVIEW:
FRESHER IMPLEMENTABILITY REVIEW:
TOKEN EFFICIENCY REVIEW:

FULL PYTEST:
INSTALL CHECK:
DIFF CHECK:
CI:

UNMAPPED_REQUIREMENTS:
UNTESTED_ACCEPTANCE_CRITERIA:
UNRESOLVED_PUBLIC_INTERFACES:
UNRESOLVED_SECURITY_INTERFACES:
UNOWNED_FUTURE_FILES:
CIRCULAR_DEPENDENCIES:
UNBOUNDED_RESIDENT_STRUCTURES:
CRITICAL_GAPS:
IMPORTANT_GAPS:
GUESS_REQUIRED_IMPLEMENTATION_ITEMS:

INTERFACE_HASH:
REQUIREMENT_MAP_HASH:
PHASE_MANIFEST_HASH:

PRODUCTION CODE MODIFIED:
NO

PH-050 IMPLEMENTED:
NO

KNOWN LIMITATIONS:

NEXT EXACT ACTION:
Independent review of the cookbook PR. After approval/merge, execute
Docs/ImplementationCookbook/execution/MASTER_EXECUTION_PROMPT.md.

STOP.

DO NOT MERGE THE PR.
DO NOT START PH-050.
