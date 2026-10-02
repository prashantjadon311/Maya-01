# Project H — Current Technical References

These sources were used to refresh V2 architecture on 2026-10-02.

## NVIDIA

- Nemotron 3 Ultra API/model:
  - https://build.nvidia.com/nvidia/nemotron-3-ultra-550b-a55b
  - https://docs.api.nvidia.com/nim/reference/nvidia-nemotron-3-ultra-550b-a55b
- NVIDIA multilingual ASR:
  - https://build.nvidia.com/nvidia/parakeet-1_1b-rnnt-multilingual-asr
- NVIDIA Speech NIM docs:
  - https://docs.nvidia.com/nim/speech/

Verified design facts:
- Nemotron 3 Ultra exposes an OpenAI-compatible hosted API.
- Streaming and tool calling are supported.
- NVIDIA documents `force_nonempty_content` for coding-agent style use.
- NVIDIA offers hosted ASR models.
- Parakeet 1.1B multilingual includes Hindi among its supported languages.

## Wake word

Official openWakeWord:
- https://github.com/dscripka/openWakeWord
- https://github.com/dscripka/openWakeWord/blob/main/README.md

Relevant facts:
- custom wake-word models supported;
- Linux supports lightweight TFLite/LiteRT and ONNX paths;
- stream processing is local;
- custom model training exists;
- optional noise suppression/VAD features exist.

## Firefox browser control

Mozilla MDN:
- Native messaging:
  https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/Native_messaging
- Native manifests:
  https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/Native_manifests
- Host permissions:
  https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/manifest.json/host_permissions
- Match patterns:
  https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/Match_patterns
- Content scripts:
  https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/Content_scripts

Design facts:
- native messaging requires explicit extension/native-host authorization;
- content scripts and host permissions can scope page access;
- native messaging is mediated through extension background code, not directly from content scripts.

## Linux tray

Freedesktop StatusNotifierItem:
- https://specifications.freedesktop.org/status-notifier-item/latest/

The protocol uses the session D-Bus and is intended for status icons/quick actions.

## Memory enforcement

systemd resource control:
- https://www.freedesktop.org/software/systemd/man/latest/systemd.resource-control.html

Design facts:
- `MemoryHigh=` is the recommended main throttling/reclaim control;
- `MemoryMax=` is the hard last-line limit.

## Offline STT rejected as V1 default

Vosk:
- https://alphacephei.com/vosk/models

Vosk's own model page says a small model is typically around 50 MB on disk but around 300 MB in runtime memory. That is why it is not the default under Project H's total 300 MiB resident cap.

## Backend / frontend

FastAPI:
- https://fastapi.tiangolo.com/tutorial/static-files/
- https://fastapi.tiangolo.com/tutorial/stream-json-lines/
- https://fastapi.tiangolo.com/advanced/events/

OpenAI Python SDK:
- https://github.com/openai/openai-python

Bootstrap 5.3:
- https://getbootstrap.com/docs/5.3/

Design facts:
- FastAPI can mount static content and stream JSON lines.
- FastAPI recommends lifespan rather than legacy startup/shutdown decorators.
- OpenAI Python supports custom base URLs, async clients and disabling SDK retries.
- Bootstrap can be used as plain compiled CSS without a frontend framework/runtime.
