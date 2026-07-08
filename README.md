# Codex Usage Viewer

To view Codex Usage for **Non-Subscribers** (such as router users).

Codex Usage Viewer is a lightweight local Codex plugin that renders a terminal
usage overview and activity heatmap from `~/.codex/sessions` token usage logs.

## Installation

Prompt Codex to install this plugin.

For example: `install JesmonX/codex-usage-viewer`.

## Usage

After installing the plugin in Codex, start a new thread and ask:

```text
Use $codex-usage-viewer
Use $codex-usage-viewer days=30
```

It shows a terminal usage panel:

<img width="1310" height="580" alt="image" src="https://github.com/user-attachments/assets/c92e38db-3491-4c8f-8029-eb342582efcb" />


The bundled script accepts one optional days argument plus an optional color mode:

```bash
python3 skills/codex-usage-viewer/scripts/usagevis.py
python3 skills/codex-usage-viewer/scripts/usagevis.py 30
python3 skills/codex-usage-viewer/scripts/usagevis.py --color always 30
```

No argument shows usage from the earliest local token record through today.
Passing a positive integer shows that many recent days. Use `--color always`
to force ANSI color when the caller has `NO_COLOR` set, or `--color never`
for plain aligned output.

The output includes estimated cost, input, output, and cached input overview
items followed by a contribution-style heatmap. The terminal layout mirrors the
main CLI activity panel while staying self-contained and dependency-free. It
intentionally does not render a terminal bars chart.

## Notes

- Reads only local `token_count` events from `~/.codex/sessions`.
- Groups dates by token-count event timestamp in `Asia/Shanghai`.
