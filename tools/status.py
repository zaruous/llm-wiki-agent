#!/usr/bin/env python3
from __future__ import annotations

"""
Project status rollup for the Project Management Wiki.

Deterministic — zero LLM calls. Reads requirement (and risk) frontmatter and
reports counts, completion rate, weighted progress, overdue items, and exit
readiness. Pairs with health.py (schema integrity) and lint.py (semantic quality).

Usage:
    python tools/status.py            # print dashboard
    python tools/status.py --json     # machine-readable output
    python tools/status.py --save     # refresh wiki/overview.md status block
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import date

# Reuse the frontmatter parser & constants from health.py (same tools/ dir).
sys.path.insert(0, str(Path(__file__).parent))
from health import (  # noqa: E402
    REPO_ROOT, WIKI_DIR, read_file, parse_frontmatter,
    DONE_STATUS, DROPPED_STATUS,
)

OVERVIEW_FILE = WIKI_DIR / "overview.md"
LOG_FILE = WIKI_DIR / "log.md"
STATUS_ORDER = [
    "proposed", "approved", "in-progress", "implemented",
    "verified", "closed", "rejected", "deferred",
]
PRIORITY_ORDER = ["must", "should", "could", "wont"]


def _pages(subdir: str) -> list[Path]:
    d = WIKI_DIR / subdir
    return sorted(d.glob("*.md")) if d.exists() else []


def _today() -> str:
    return date.today().isoformat()


def run_status() -> dict:
    status_counts = {s: 0 for s in STATUS_ORDER}
    priority_counts = {p: 0 for p in PRIORITY_ORDER}
    overdue: list[dict] = []
    must_open: list[str] = []
    active_progress: list[int] = []
    done = 0
    dropped = 0
    today = _today()

    reqs = _pages("requirements")
    for p in reqs:
        fm = parse_frontmatter(read_file(p))
        status = str(fm.get("status", "")).strip()
        priority = str(fm.get("priority", "")).strip()
        rid = str(fm.get("id", p.stem))

        if status in status_counts:
            status_counts[status] += 1
        if priority in priority_counts:
            priority_counts[priority] += 1

        is_done = status in DONE_STATUS
        is_dropped = status in DROPPED_STATUS
        done += is_done
        dropped += is_dropped

        if not is_done and not is_dropped:
            # active requirement
            try:
                active_progress.append(int(fm.get("progress", 0)))
            except (TypeError, ValueError):
                active_progress.append(0)
            due = str(fm.get("due_date", "")).strip()
            if due and due < today:
                overdue.append({"id": rid, "due_date": due, "status": status,
                                "owner": str(fm.get("owner", ""))})
            if priority == "must":
                must_open.append(rid)

    total = len(reqs)
    denom = total - dropped  # exclude rejected/deferred from completion base
    completion_rate = round(100 * done / denom, 1) if denom else 0.0
    weighted_progress = round(sum(active_progress) / len(active_progress), 1) if active_progress else (100.0 if total and not active_progress else 0.0)

    # open high-impact risks
    open_high_risks = []
    for p in _pages("risks"):
        fm = parse_frontmatter(read_file(p))
        if str(fm.get("status", "open")).strip() == "open" and str(fm.get("impact", "")).strip() == "high":
            open_high_risks.append(str(fm.get("id", p.stem)))

    exit_ready = (total > 0 and not must_open and not overdue and not open_high_risks)

    return {
        "date": today,
        "total_requirements": total,
        "status_counts": status_counts,
        "priority_counts": priority_counts,
        "done": done,
        "dropped": dropped,
        "completion_rate": completion_rate,
        "weighted_progress": weighted_progress,
        "overdue": overdue,
        "must_open": must_open,
        "open_high_risks": open_high_risks,
        "exit_ready": exit_ready,
    }


def format_report(r: dict) -> str:
    lines = [
        f"# Project Status - {r['date']}",
        "",
        f"- **Total requirements:** {r['total_requirements']}",
        f"- **Completion rate:** {r['completion_rate']}%  "
        f"({r['done']} done / {r['total_requirements'] - r['dropped']} in base)",
        f"- **Weighted progress (active):** {r['weighted_progress']}%",
        f"- **Exit readiness:** {'ready' if r['exit_ready'] else 'not ready'}",
        "",
        "## Requirements by Status",
        "| " + " | ".join(r["status_counts"].keys()) + " |",
        "|" + "---|" * len(r["status_counts"]),
        "| " + " | ".join(str(v) for v in r["status_counts"].values()) + " |",
        "",
        "## Requirements by Priority (MoSCoW)",
        "| " + " | ".join(r["priority_counts"].keys()) + " |",
        "|" + "---|" * len(r["priority_counts"]),
        "| " + " | ".join(str(v) for v in r["priority_counts"].values()) + " |",
        "",
    ]

    lines.append(f"## Overdue ({len(r['overdue'])})")
    if r["overdue"]:
        lines.append("| ID | Due | Status | Owner |")
        lines.append("|---|---|---|---|")
        for o in r["overdue"]:
            lines.append(f"| {o['id']} | {o['due_date']} | {o['status']} | {o['owner']} |")
    else:
        lines.append("No overdue active requirements.")
    lines.append("")

    lines.append("## Exit Gates")
    lines.append(f"- Open `must` requirements: {len(r['must_open'])} "
                 + (f"({', '.join(r['must_open'])})" if r["must_open"] else "OK"))
    lines.append(f"- Overdue requirements: {len(r['overdue'])} " + ("" if r["overdue"] else "OK"))
    lines.append(f"- Open `high` risks: {len(r['open_high_risks'])} "
                 + (f"({', '.join(r['open_high_risks'])})" if r["open_high_risks"] else "OK"))
    lines.append("- Exit Criteria (manual): review `wiki/scope/scope.md`")
    lines.append("")
    return "\n".join(lines)


def _table(headers: list[str], values: list[str | int]) -> list[str]:
    return [
        "| " + " | ".join(headers) + " |",
        "|" + "---|" * len(headers),
        "| " + " | ".join(str(v) for v in values) + " |",
    ]


def format_overview(r: dict) -> str:
    overdue_lines = ["- None."] if not r["overdue"] else [
        f"- {o['id']} - due {o['due_date']} - {o['status']} - owner: {o['owner'] or '(unassigned)'}"
        for o in r["overdue"]
    ]
    risk_lines = ["- None."] if not r["open_high_risks"] else [
        f"- [[{rid}]]" for rid in r["open_high_risks"]
    ]
    must_gate = "OK" if not r["must_open"] else ", ".join(r["must_open"])
    overdue_gate = "OK" if not r["overdue"] else str(len(r["overdue"]))
    risk_gate = "OK" if not r["open_high_risks"] else ", ".join(r["open_high_risks"])

    lines = [
        "---",
        'title: "Project Overview / Dashboard"',
        "type: synthesis",
        "tags: []",
        f"last_updated: {r['date']}",
        "---",
        "",
        "# Project Overview",
        "",
        "*Maintained by the agent. Refreshed by `python tools/status.py --save`.*",
        "",
        "## Status at a Glance",
        f"- **Total requirements:** {r['total_requirements']}",
        f"- **Completion rate:** {r['completion_rate']}% ({r['done']} done / {r['total_requirements'] - r['dropped']} in base)",
        f"- **Weighted progress:** {r['weighted_progress']}%",
        f"- **Exit readiness:** {'ready' if r['exit_ready'] else 'not ready'}",
        "",
        "## Requirements by Status",
        *_table(STATUS_ORDER, [r["status_counts"][s] for s in STATUS_ORDER]),
        "",
        "## Requirements by Priority (MoSCoW)",
        *_table(PRIORITY_ORDER, [r["priority_counts"][p] for p in PRIORITY_ORDER]),
        "",
        "## Overdue / At-Risk",
        *overdue_lines,
        "",
        "## Open Risks",
        *risk_lines,
        "",
        "## Exit Gates",
        f"- Open `must` requirements: {must_gate}",
        f"- Overdue active requirements: {overdue_gate}",
        f"- Open `high` risks: {risk_gate}",
        "- Exit Criteria (manual): review `wiki/scope/scope.md`",
        "",
    ]
    if r["total_requirements"] == 0:
        lines.extend([
            "---",
            "",
            "No interviews ingested yet. Add the first one:",
            "",
            "```",
            "ingest raw/interviews/<file>.md",
            "```",
            "",
        ])
    return "\n".join(lines)


def append_log(entry: str):
    existing = read_file(LOG_FILE).rstrip()
    text = entry.strip()
    if existing:
        LOG_FILE.write_text(existing + "\n\n" + text + "\n", encoding="utf-8")
    else:
        LOG_FILE.write_text("# Wiki Log\n\n" + text + "\n", encoding="utf-8")


def save_overview(r: dict):
    OVERVIEW_FILE.write_text(format_overview(r), encoding="utf-8")
    append_log(f"## [{r['date']}] status | Project status refreshed\n\nUpdated wiki/overview.md from deterministic status rollup.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Project status rollup for the Project Wiki (deterministic, no LLM calls)"
    )
    parser.add_argument("--json", action="store_true", help="Machine-readable JSON output")
    parser.add_argument("--save", action="store_true",
                        help="Refresh wiki/overview.md with the latest status rollup")
    args = parser.parse_args()

    results = run_status()
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(format_report(results))
    if args.save:
        save_overview(results)
        print(f"Saved: {OVERVIEW_FILE.relative_to(REPO_ROOT)}")
