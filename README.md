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

It shows a terminal usage panel. Example 30-day output:

```text
╭───────── Total tokens Activity ─────────╮
│                                         │
│  Cost     Input    Output  Cache        │
│  $791.33  674.33M  5.01M   606.78M      │
│  gpt-5.5                   90.0%        │
│                                         │
│  2026-06-09 to 2026-07-08  total=680.05M│
│                                         │
│     Jun      Jul                        │
│Mon     ▓▓ ▒▒    ██                      │
│Tue  ░░ ▒▒    ▒▒ ██                      │
│Wed  ██ ██ ▓▓ ▓▓ ▒▒                      │
│Thu  ▓▓ ██ ▒▒ ▒▒                         │
│Fri  ██       ░░                         │
│Sat  ▓▓ ░░ ░░ ██                         │
│Sun  ░░ ░░ ░░ ▓▓                         │
│                                         │
│     Less ░░ ▒▒ ▓▓ ██ More               │
│     plain-4 / comfortable / total_tokens│
│                                         │
╰─────────────────────────────────────────╯
```

The bundled script accepts one optional days argument plus an optional color mode:

```bash
python3 skills/codex-usage-viewer/scripts/usagevis.py
python3 skills/codex-usage-viewer/scripts/usagevis.py 30
python3 skills/codex-usage-viewer/scripts/usagevis.py --color never 30
python3 skills/codex-usage-viewer/scripts/usagevis.py --color always 30
```

No argument shows usage from the earliest local token record through today.
Passing a positive integer shows that many recent days. The Codex plugin uses
`--color never` by default so the output displays faster in Codex without
replaying many ANSI escape sequences. Use `--color always` manually when you
prefer colored terminal output.

The output includes estimated cost, input, output, and cached input overview
items followed by a contribution-style heatmap. The overview keeps the four
main values compact and only shows model name plus cache hit rate in the detail
row. Plain output uses four visible block-glyph intensity levels without dot
markers. The terminal layout mirrors the main CLI activity panel while staying
self-contained and dependency-free. It intentionally does not render a terminal
bars chart.

## Notes

- Reads only local `token_count` events from `~/.codex/sessions`.
- Groups dates by token-count event timestamp in `Asia/Shanghai`.
