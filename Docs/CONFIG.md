# Project H — Configuration and Action Packs

## 1. Config location

```text
~/.config/project-h/
├── config.toml
├── actions.d/
│   ├── core.json
│   ├── developer.json
│   └── personal.json
├── wake/
│   └── assistant_name.tflite
└── extension/
    └── state.json
```

Secrets use environment variables in V1.

## 2. Canonical config example

```toml
[assistant]
display_name = "Maya"
wake_phrase = "Maya"
language = "auto"
start_on_login = true

[voice]
enabled = true
always_listen = false
push_to_talk_hotkey = "Ctrl+Space"
wake_engine = "openwakeword"
wake_model = "~/.config/project-h/wake/assistant_name.tflite"
wake_threshold = 0.55
vad_enabled = true
max_command_seconds = 30
retain_command_audio = false

[stt]
provider = "nvidia"
model = "nvidia/parakeet-1_1b-rnnt-multilingual-asr"
api_key_env = "NVIDIA_API_KEY"
default_language = "hi-IN"

[ai]
provider = "nvidia"
base_url = "https://integrate.api.nvidia.com/v1"
model = "nvidia/nemotron-3-ultra-550b-a55b"
api_key_env = "NVIDIA_API_KEY"
timeout_seconds = 120
reasoning_effort = "medium"
reasoning_budget = 4096
max_output_tokens = 8192

[dashboard]
host = "127.0.0.1"
port = 8765
open_browser = true

[agents]
max_active = 1
max_steps = 30
max_api_calls_per_task = 20
default_timeout_minutes = 30

[resources]
memory_high_mb = 240
memory_max_mb = 300
max_event_queue = 256
max_audio_command_seconds = 30

[privacy]
store_chat_history = true
store_action_audit = true
log_prompt_content = false
log_response_content = false
retain_audio = false
```

Values are examples. Validate the actual NVIDIA STT identifier/API integration during implementation because hosted model naming and function IDs can change.

## 3. Browser allowlist

```toml
[[browser.domains]]
pattern = "https://www.google.com/*"
enabled = true
capabilities = ["open", "read", "click", "type", "submit"]
adapter = "google"

[[browser.domains]]
pattern = "https://www.amazon.in/*"
enabled = true
capabilities = ["open", "read", "click", "type", "submit"]
adapter = "amazon"

[[browser.domains]]
pattern = "https://chatgpt.com/*"
enabled = true
capabilities = ["open", "read", "click", "type", "submit"]
adapter = "chatgpt"

[[browser.domains]]
pattern = "https://gemini.google.com/*"
enabled = true
capabilities = ["open", "read", "click", "type", "submit"]
adapter = "gemini"

[[browser.domains]]
pattern = "https://claude.ai/*"
enabled = true
capabilities = ["open", "read", "click", "type", "submit"]
adapter = "claude"
```

The extension needs corresponding Firefox host permissions. Dashboard should show:
- Project H policy status;
- browser-permission status;
- adapter status.

## 4. File roots

```toml
[[files.roots]]
path = "~/Projects"
read = true
write = true
delete = false

[[files.roots]]
path = "~/Downloads"
read = true
write = false
delete = false
```

## 5. Action pack format

`actions.d/core.json`:

```json
{
  "schema_version": 1,
  "pack_id": "core",
  "label": "Core actions",
  "actions": [
    {
      "id": "app.open_vscode",
      "enabled": true,
      "phrases": [
        "open vscode",
        "vs code kholo"
      ],
      "executor": "process",
      "arguments": {
        "argv": ["code"]
      },
      "approval": "preapproved",
      "risk": "low",
      "timeout_seconds": 10
    },
    {
      "id": "browser.google_search",
      "enabled": true,
      "phrases": [
        "google search {query}",
        "google par {query} search karo"
      ],
      "executor": "browser",
      "arguments": {
        "operation": "search",
        "adapter": "google",
        "query": "{query}"
      },
      "approval": "preapproved",
      "risk": "low"
    }
  ]
}
```

## 6. Developer preapproval rules

Separate from phrase actions:

```json
{
  "schema_version": 1,
  "rules": [
    {
      "id": "git-status",
      "executable": "git",
      "argv_prefix": ["status"],
      "working_roots": ["~/Projects"],
      "approval": "preapproved",
      "timeout_seconds": 20
    },
    {
      "id": "pytest",
      "executable": "pytest",
      "argv_prefix": [],
      "working_roots": ["~/Projects"],
      "approval": "preapproved",
      "timeout_seconds": 600
    }
  ]
}
```

## 7. JSON design rules

- UTF-8.
- reject unknown top-level/action fields;
- unique IDs;
- atomic write (`temp -> fsync -> rename`);
- keep `.bak` of last valid config;
- validate before replacing active config;
- never execute an action simply because JSON parsed;
- no shell script body in JSON;
- no Python code in JSON;
- composite actions may only reference registered action IDs.

## 8. Dashboard editor

Do not force users to manually edit JSON.

Dashboard provides:
- list actions;
- enable/disable;
- phrase patterns;
- risk;
- approval;
- executor arguments;
- test/dry-run;
- raw JSON advanced editor;
- schema errors with exact path.

Any dashboard save must produce valid canonical JSON.
