# Codex Usage Viewer
To view Codex Usage for **Non-Subscribers**(such as router users).

Codex Usage Viewer is a lightweight local Codex plugin that renders a terminal activity heatmap from `~/.codex/sessions` token usage logs.

## Installation
Prompt codex to install this.

Such as `install JesmonX/codex-usage-viewer`.

## Usage

After installing the plugin in Codex, start a new thread and ask:

```text
Use $codex-usage-viewer
Use $codex-usage-viewer days=30
```

The bundled script accepts one optional argument:

```bash
python3 skills/codex-usage-viewer/scripts/usagevis.py
python3 skills/codex-usage-viewer/scripts/usagevis.py 30
```

No argument shows usage from the earliest local token record through today.
Passing a positive integer shows that many recent days.

## Notes

- Reads only local `token_count` events from `~/.codex/sessions`.
- Groups dates by token-count event timestamp in `Asia/Shanghai`.
- Does not export message content.
- `/usagevis` is included as a skill trigger phrase, but native custom slash command registration depends on Codex client support.
