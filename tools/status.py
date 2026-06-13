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
    VALID_STATUS, VALID_PRIORITY, DONE_STATUS, DROPPED_STATUS,
)


def _pages(subdir: str) -> list[Path]:
    d = WIKI_DIR / subdir
    return sorted(d.glob("*.md")) if d.exists() else []


def _today() -> str:
    return date.today().isoformat()


def run_status() -> dict:
    status_counts = {s: 0 for s in VALID_STATUS}
    priority_counts = {p: 0 for p in VALID_PRIORITY}
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
        f"# Project Status — {r['date']}",
        "",
        f"- **Total requirements:** {r['total_requirements']}",
        f"- **Completion rate:** {r['completion_rate']}%  "
        f"({r['done']} done / {r['total_requirements'] - r['dropped']} in base)",
        f"- **Weighted progress (active):** {r['weighted_progress']}%",
        f"- **Exit readiness:** {'✅ ready' if r['exit_ready'] else '❌ not ready'}",
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
        lines.append("No overdue active requirements. ✅")
    lines.append("")

    lines.append("## Exit Gates")
    lines.append(f"- Open `must` requirements: {len(r['must_open'])} "
                 + (f"({', '.join(r['must_open'])})" if r["must_open"] else "✅"))
    lines.append(f"- Overdue requirements: {len(r['overdue'])} " + ("" if r["overdue"] else "✅"))
    lines.append(f"- Open `high` risks: {len(r['open_high_risks'])} "
                 + (f"({', '.join(r['open_high_risks'])})" if r["open_high_risks"] else "✅"))
    lines.append("- Exit Criteria (manual): review `wiki/scope/scope.md`")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Project status rollup for the Project Wiki (deterministic, no LLM calls)"
    )
    parser.add_argument("--json", action="store_true", help="Machine-readable JSON output")
    parser.add_argument("--save", action="store_true",
                        help="(reserved) refresh wiki/overview.md status block")
    args = parser.parse_args()

    results = run_status()
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(format_report(results))
