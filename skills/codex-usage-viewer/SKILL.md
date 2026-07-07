---
name: codex-usage-viewer
description: Render a terminal activity heatmap of local Codex token usage from ~/.codex/sessions. Use when the user asks for Codex usage visualization, token usage, usage activity, contribution-style heatmap, usagevis, /usagevis, or recent-days Codex usage.
---

# Codex Usage Viewer

Run the bundled script to show a local Codex usage overview and activity graph.

## Workflow

1. Extract at most one positive integer `days` value from the user's request.
   - `/usagevis 30`, `usagevis 30`, `days=30`, and `recent 30 days` all mean `30`.
   - If no days value is present, omit the argument so the script starts at the earliest usage record.
2. Run:

```bash
python3 <this-skill>/scripts/usagevis.py --color always [days]
```

3. Return the overview and activity graph output directly as raw terminal output. Do not wrap it in a Markdown code block, and do not add bars, Top Days, Top Working Directories, CSV, JSON, or HTML reports.

## Notes

- The script reads only local `token_count` events from `~/.codex/sessions`.
- Dates are grouped by each `token_count` event timestamp in `Asia/Shanghai`.
- The overview shows estimated cost, input, output, and cached input using the bundled default price profile.
- `--color always` is used so Codex plugin output can preserve ANSI color even when `NO_COLOR` is set in the execution environment.
- Message content is not exported or displayed.
- `/usagevis` is treated as a trigger phrase for this skill. If the active Codex client intercepts unknown slash commands before they reach the model, use `usagevis` or `Use $codex-usage-viewer` instead.
