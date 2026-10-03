# Maya Implementation Cookbook — Freeze Manifest

- **Cookbook Version:** `1.0.0`
- **Status:** `FROZEN`
- **Repository:** `prashantjadon311/Maya-01`

- **Cookbook Work Base SHA:** `d603173624ddc9285b32ee00f33c10be2ecc9b58`
- **Product Code Base SHA:** `ef00714c86d3d7b5684d693da35aa82595a088d4`
- **CI Baseline Run:** `37107781413` (Green on base SHA)
- **Target OS:** Ubuntu Linux (x86_64)
- **Python Floor:** `>=3.11` (Runtime verification on Python 3.14)

---

## 1. Baseline Rationale

As ruled in the execution charter:
1. `COOKBOOK_WORK_BASE_SHA` (`d603173624ddc9285b32ee00f33c10be2ecc9b58`): The snapshot from which cookbook generation work begins (contains the compiler specification and execution plan).
2. `PRODUCT_CODE_BASE_SHA` (`ef00714c86d3d7b5684d693da35aa82595a088d4`): The last production-code state before cookbook documents were added. Analysis of existing PH-000 through PH-040 production code anchors on this baseline.

---

## 2. Authority Document Hashes

| Authority Document | Precedence | Blob SHA |
| :--- | :--- | :--- |
| `Docs/DOCS.md` | 1 | `f0661e12eb37d7cb35468fb998d24e3be9ca61a0` |
| `Docs/SECURITY.md` | 2 | `018eddf2c193818f2e54f38dfe24639aac8af395` |
| `Docs/ARCHITECTURE.md` | 3 | `60c03ec8ef6122409da8c56020896dfe9f26bbd6` |
| `Docs/CONFIG.md` | 4 | `0df558337f3fe51a90f7eef6369b22218309879f` |
| `Docs/UI.md` | 5 | `33599d1fe7c09f3cd558824bcd13826dd958b302` |
| `Docs/PLAN.md` | 6 | `317d8e583903d901310755ca96db5eab8f090399` |
| `Docs/TASKS.md` | 7 | `f2b8f60c28f023946a3e3c4376c0bba14f585902` |
| `Docs/EXECUTION.md` | 8 | `4a41e269f1a46146e87b83829560294b85890563` |
| `Docs/SKILL.md` | Meta/Instructional | `3ee7bf617703e36bda264096154bc2609950deea` |

---

## 3. Mandatory Freeze Counters

At freeze, all mandatory counters must strictly equal zero:

```text
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
```

---

## 4. Canonical Fingerprints
- `INTERFACE_HASH`: `292b708a255e68139ed519804ea3d1cee3286678867e84d3c71475c8d05ed0d3`
- `REQUIREMENT_MAP_HASH`: `d324fe6804d8057a01b2534200a0babb439115bc449e561b0cd1928515656274`
- `PHASE_MANIFEST_HASH`: `333541a149349fcbef615e723a22cc67f29128dd9d23e7a7c0a58679c40c699b`
