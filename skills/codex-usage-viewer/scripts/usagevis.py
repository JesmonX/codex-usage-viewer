#!/usr/bin/env python3
"""Render a local Codex usage activity graph from ~/.codex/sessions."""

from __future__ import annotations

import argparse
import calendar
import json
import math
import os
import re
import shutil
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any


TOKEN_KEYS = (
    "input_tokens",
    "cached_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
    "total_tokens",
)
LOCAL_TZ = timezone(timedelta(hours=8), name="Asia/Shanghai")
SESSIONS_DIR = Path("~/.codex/sessions").expanduser()
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
GLYPHS_WIDE = ("··", "░░", "▒▒", "▓▓", "██")
GLYPHS_NARROW = ("·", "░", "▒", "▓", "█")
PALETTE = ("#374151", "#4ade80", "#22c55e", "#a3e635", "#facc15")
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
PRICE_PROFILE = {
    "model": "gpt-5.5",
    "context": "short",
    "input_per_million": 5.00,
    "cached_input_per_million": 0.50,
    "output_per_million": 30.00,
}
COLOR_MODE = "auto"


def parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=LOCAL_TZ)
    return parsed.astimezone(LOCAL_TZ)


def empty_usage() -> dict[str, int]:
    return {key: 0 for key in TOKEN_KEYS}


def normalize_usage(value: dict[str, Any]) -> dict[str, int]:
    return {key: int(value.get(key) or 0) for key in TOKEN_KEYS}


def delta_usage(current: dict[str, int], previous: dict[str, int]) -> dict[str, int]:
    return {key: max(0, current.get(key, 0) - previous.get(key, 0)) for key in TOKEN_KEYS}


def add_usage(target: dict[str, int], usage: dict[str, int]) -> None:
    for key in TOKEN_KEYS:
        target[key] += int(usage.get(key) or 0)


def format_tokens(value: int) -> str:
    if value >= 1_000_000_000:
        return "%.2fB" % (value / 1_000_000_000)
    if value >= 1_000_000:
        return "%.2fM" % (value / 1_000_000)
    if value >= 1_000:
        return "%.1fK" % (value / 1_000)
    return str(value)


def format_cost(value: float) -> str:
    if value >= 1000:
        return "$%s" % format(value, ",.2f")
    if value >= 1:
        return "$%.2f" % value
    return "$%.4f" % value


def billable_input_tokens(usage: dict[str, Any]) -> int:
    return max(0, int(usage.get("input_tokens") or 0) - int(usage.get("cached_input_tokens") or 0))


def pct(value: int, total: int) -> str:
    if total <= 0:
        return "0.0%"
    return "%.1f%%" % (100.0 * value / total)


def estimate_usage_cost(usage: dict[str, Any]) -> float:
    return (
        billable_input_tokens(usage) * PRICE_PROFILE["input_per_million"]
        + int(usage.get("cached_input_tokens") or 0) * PRICE_PROFILE["cached_input_per_million"]
        + int(usage.get("output_tokens") or 0) * PRICE_PROFILE["output_per_million"]
    ) / 1_000_000.0


def iter_session_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*.jsonl") if path.is_file())


def read_usage_events(path: Path) -> list[tuple[date, dict[str, int]]]:
    events: list[tuple[date, dict[str, int]]] = []
    previous_total: dict[str, int] | None = None
    try:
        handle = path.open("r", encoding="utf-8")
    except OSError:
        return events

    with handle:
        for raw_line in handle:
            try:
                item = json.loads(raw_line)
            except json.JSONDecodeError:
                continue
            payload = item.get("payload") or {}
            if item.get("type") != "event_msg" or payload.get("type") != "token_count":
                continue

            info = payload.get("info") or {}
            total_raw = info.get("total_token_usage") or {}
            last_raw = info.get("last_token_usage") or {}
            usage: dict[str, int] | None = None
            if last_raw:
                usage = normalize_usage(last_raw)
            elif total_raw:
                current_total = normalize_usage(total_raw)
                usage = current_total if previous_total is None else delta_usage(current_total, previous_total)

            if total_raw:
                previous_total = normalize_usage(total_raw)
            event_dt = parse_timestamp(item.get("timestamp"))
            if usage is not None and event_dt is not None:
                events.append((event_dt.date(), usage))
    return events


def load_events() -> list[tuple[date, dict[str, int]]]:
    events: list[tuple[date, dict[str, int]]] = []
    for path in iter_session_files(SESSIONS_DIR):
        events.extend(read_usage_events(path))
    return events


def day_range(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def aggregate(events: list[tuple[date, dict[str, int]]], start: date, end: date) -> list[dict[str, Any]]:
    daily = defaultdict(empty_usage)
    for event_date, usage in events:
        if start <= event_date <= end:
            add_usage(daily[event_date], usage)
    rows: list[dict[str, Any]] = []
    for current in day_range(start, end):
        row = {"date": current, **daily[current]}
        rows.append(row)
    return rows


def summarize(rows: list[dict[str, Any]]) -> dict[str, int]:
    totals = empty_usage()
    for row in rows:
        add_usage(totals, row)
    return totals


def overview_items(rows: list[dict[str, Any]]) -> list[tuple[str, str, str]]:
    totals = summarize(rows)
    return [
        (
            "Cost",
            format_cost(estimate_usage_cost(totals)),
            "%s/%s\nestimate" % (PRICE_PROFILE["model"], PRICE_PROFILE["context"]),
        ),
        (
            "Input",
            format_tokens(totals["input_tokens"]),
            "%s\nbillable" % format_tokens(billable_input_tokens(totals)),
        ),
        (
            "Output",
            format_tokens(totals["output_tokens"]),
            "%s\nreasoning" % format_tokens(totals["reasoning_output_tokens"]),
        ),
        (
            "Cache",
            format_tokens(totals["cached_input_tokens"]),
            "%s of input" % pct(totals["cached_input_tokens"], totals["input_tokens"]),
        ),
    ]


def overview_lines(rows: list[dict[str, Any]]) -> list[str]:
    items = overview_items(rows)
    widths = [max(len(label), len(value), *(len(part) for part in detail.split("\n"))) for label, value, detail in items]
    lines = []
    for row_index in range(4):
        cells = []
        for width, (label, value, detail) in zip(widths, items):
            detail_parts = detail.split("\n")
            if row_index == 0:
                cell = dim(label.ljust(width))
            elif row_index == 1:
                cell = color(value.ljust(width), PALETTE[-1], bold=True)
            else:
                detail_index = row_index - 2
                cell = dim((detail_parts[detail_index] if detail_index < len(detail_parts) else "").ljust(width))
            cells.append(cell)
        lines.append("  " + "  ".join(cells))
    return lines


def quantile(values: list[int], fraction: float) -> int:
    if not values:
        return 0
    index = int(math.floor((len(values) - 1) * fraction))
    return values[min(max(index, 0), len(values) - 1)]


def thresholds(rows: list[dict[str, Any]]) -> list[int]:
    values = sorted(int(row["total_tokens"]) for row in rows if int(row["total_tokens"]) > 0)
    if not values:
        return []
    return [quantile(values, fraction) for fraction in (0.25, 0.50, 0.75, 0.90)]


def activity_level(value: int, levels: list[int]) -> int:
    if value <= 0 or not levels:
        return 0
    level = 1
    for threshold in levels:
        if value > threshold:
            level += 1
    return min(level, 4)


def build_weeks(rows: list[dict[str, Any]]) -> tuple[list[str], list[list[dict[str, Any] | None]]]:
    rows_by_date = {row["date"]: row for row in rows}
    start = rows[0]["date"]
    end = rows[-1]["date"]
    grid_start = start - timedelta(days=start.weekday())
    grid_end = end + timedelta(days=6 - end.weekday())

    labels: list[str] = []
    weeks: list[list[dict[str, Any] | None]] = []
    current = grid_start
    while current <= grid_end:
        week: list[dict[str, Any] | None] = []
        label = ""
        for offset in range(7):
            day = current + timedelta(days=offset)
            if start <= day <= end:
                week.append(rows_by_date.get(day))
                if day.day == 1:
                    label = calendar.month_abbr[day.month]
            else:
                week.append(None)
        if not labels:
            label = calendar.month_abbr[max(start, current).month]
        labels.append(label)
        weeks.append(week)
        current += timedelta(days=7)
    return labels, weeks


def use_color() -> bool:
    if COLOR_MODE == "always":
        return True
    if COLOR_MODE == "never":
        return False
    return os.environ.get("NO_COLOR") is None and os.environ.get("TERM") != "dumb"


def color(text: str, hex_color: str, *, bold: bool = False) -> str:
    if not use_color():
        return text
    red = int(hex_color[1:3], 16)
    green = int(hex_color[3:5], 16)
    blue = int(hex_color[5:7], 16)
    prefix = "1;" if bold else ""
    return f"\033[{prefix}38;2;{red};{green};{blue}m{text}\033[0m"


def dim(text: str) -> str:
    if not use_color():
        return text
    return f"\033[2m{text}\033[0m"


def visible_len(text: str) -> int:
    return len(ANSI_RE.sub("", text))


def pad_visible(text: str, width: int) -> str:
    return text + " " * max(0, width - visible_len(text))


def panel(lines: list[str], title: str, width: int | None = None) -> str:
    content_width = max(visible_len(line) for line in lines)
    title_text = f" {title} "
    width = max(width or 0, content_width, len(title_text) + 2)
    top_left = "╭"
    top_right = "╮"
    bottom_left = "╰"
    bottom_right = "╯"
    horizontal = "─"
    top_gap = max(0, width - len(title_text))
    top = top_left + horizontal * (top_gap // 2) + title_text + horizontal * (top_gap - top_gap // 2) + top_right
    bottom = bottom_left + horizontal * width + bottom_right
    body = [color("│", PALETTE[-1]) + pad_visible(line, width) + color("│", PALETTE[-1]) for line in lines]
    return "\n".join([color(top, PALETTE[-1]), *body, color(bottom, PALETTE[-1])])


def choose_density(week_count: int, terminal_width: int) -> str:
    comfortable_width = 12 + week_count * 3
    return "comfortable" if comfortable_width <= max(50, terminal_width - 4) else "compact"


def activity_stride(density: str) -> int:
    return 3 if density == "comfortable" else 1


def render_band(
    labels: list[str],
    weeks: list[list[dict[str, Any] | None]],
    levels: list[int],
    stride: int,
    start_index: int,
    end_index: int,
) -> list[str]:
    glyphs = GLYPHS_WIDE if stride > 1 else GLYPHS_NARROW
    chunk_labels = labels[start_index:end_index]
    chunk_weeks = weeks[start_index:end_index]
    month_chars = [" "] * (len(chunk_weeks) * stride + 2)
    for index, label in enumerate(chunk_labels):
        if not label:
            continue
        offset = index * stride
        for char_index, char in enumerate(label[:3]):
            if offset + char_index < len(month_chars):
                month_chars[offset + char_index] = char

    lines = ["     " + dim("".join(month_chars).rstrip())]
    for weekday_index, weekday in enumerate(WEEKDAYS):
        line = dim(f"{weekday}  ")
        for week in chunk_weeks:
            row = week[weekday_index]
            if row is None:
                line += " " * stride
                continue
            level = activity_level(int(row["total_tokens"]), levels)
            glyph = glyphs[level]
            line += color(glyph, PALETTE[level], bold=level > 0)
            if stride > 1:
                line += " "
        lines.append(line.rstrip())
    return lines


def render_activity(rows: list[dict[str, Any]], start: date, end: date) -> str:
    labels, weeks = build_weeks(rows)
    levels = thresholds(rows)
    total = sum(int(row["total_tokens"]) for row in rows)
    terminal_width = shutil.get_terminal_size((100, 24)).columns
    density = choose_density(len(weeks), terminal_width)
    stride = activity_stride(density)
    inner_budget = max(42, terminal_width - 4)
    weeks_per_band = max(4, (inner_budget - 9) // stride)

    blocks: list[str] = []
    for start_index in range(0, len(weeks), weeks_per_band):
        end_index = min(len(weeks), start_index + weeks_per_band)
        lines = [
            "",
            *overview_lines(rows),
            "",
            "  " + dim(start.isoformat() + " to " + end.isoformat() + "  ")
            + color("total=%s" % format_tokens(total), PALETTE[-1], bold=True),
            "",
            *render_band(labels, weeks, levels, stride, start_index, end_index),
            "",
        ]
        legend = "     " + dim("Less ")
        glyphs = GLYPHS_WIDE if stride > 1 else GLYPHS_NARROW
        for level, glyph in enumerate(glyphs):
            legend += color(glyph, PALETTE[level], bold=level > 0) + " "
        legend += dim("More")
        footer = "     " + dim("bright / %s / total_tokens" % density)
        if len(weeks) > weeks_per_band:
            band_start = weeks[start_index][0] or next(day for day in weeks[start_index] if day)
            band_end = weeks[end_index - 1][-1] or next(day for day in reversed(weeks[end_index - 1]) if day)
            footer += dim(" / %s..%s" % (band_start["date"].isoformat(), band_end["date"].isoformat()))
        lines.extend([legend, footer, ""])
        width = max(visible_len(line) for line in lines)
        blocks.append(panel(lines, "Total tokens Activity", width))
    return "\n\n".join(blocks)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Show a Codex usage activity graph. Optional argument: days."
    )
    parser.add_argument("days", nargs="?", type=int, help="Days ending today; omit to start at the earliest usage record.")
    parser.add_argument(
        "--color",
        choices=("auto", "always", "never"),
        default="auto",
        help="Color output mode. Default: auto.",
    )
    args = parser.parse_args(argv)
    if args.days is not None and args.days <= 0:
        parser.error("days must be a positive integer")
    return args


def main(argv: list[str] | None = None) -> int:
    global COLOR_MODE
    args = parse_args(argv)
    COLOR_MODE = args.color
    events = load_events()
    if not events:
        print("No Codex token usage found in %s." % SESSIONS_DIR)
        return 0

    today = datetime.now(LOCAL_TZ).date()
    if args.days is None:
        start = min(event_date for event_date, _ in events)
    else:
        start = today - timedelta(days=args.days - 1)
    rows = aggregate(events, start, today)
    print(render_activity(rows, start, today))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
