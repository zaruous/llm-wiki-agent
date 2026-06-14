#!/usr/bin/env python3
from __future__ import annotations

"""
Deterministic requirement lifecycle updates for the Project Wiki.

Usage:
    python tools/requirement.py approve REQ-012 --owner Kim --start-date 2026-06-16 --due-date 2026-06-27 --wbs-id 1.2.3 --decision DEC-003
    python tools/requirement.py progress REQ-012 --progress 40 --status in-progress --note "OCR API done"
    python tools/requirement.py complete REQ-012 --status verified --decision DEC-004
    python tools/requirement.py drop REQ-019 --status deferred --reason "Budget hold [[DEC-011]]"

The tool updates:
  - wiki/requirements/REQ-XXX.md frontmatter
  - the requirement Status / Schedule Log section
  - wiki/scope/scope.md WBS row when the requirement has a wbs_id
  - wiki/log.md
"""

import argparse
import re
import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent))
from health import REPO_ROOT, WIKI_DIR, read_file, parse_frontmatter  # noqa: E402

SCOPE_FILE = WIKI_DIR / "scope" / "scope.md"
LOG_FILE = WIKI_DIR / "log.md"
REQ_DIR = WIKI_DIR / "requirements"

FIELD_ORDER = [
    "id", "title", "type", "category", "priority", "status",
    "source_interviews", "wbs_id", "owner", "assignees", "progress",
    "start_date", "due_date", "completed_date", "dropped_date",
    "dropped_reason", "depends_on", "milestone", "tags", "last_updated",
]
LIST_KEYS = {"source_interviews", "assignees", "depends_on", "tags"}
QUOTE_KEYS = {"title", "wbs_id", "owner", "completed_date", "dropped_date", "dropped_reason", "start_date", "due_date", "milestone"}
ACTIVE_STATUSES = {"approved", "in-progress", "implemented"}
DONE_STATUSES = {"verified", "closed"}
DROPPED_STATUSES = {"rejected", "deferred"}


def today() -> str:
    return date.today().isoformat()


def req_path(req_id: str) -> Path:
    rid = req_id.upper()
    return REQ_DIR / f"{rid}.md"


def split_frontmatter(content: str) -> tuple[dict, str]:
    if not content.startswith("---"):
        raise ValueError("requirement page has no frontmatter")
    end = content.find("\n---", 3)
    if end == -1:
        raise ValueError("requirement page has unclosed frontmatter")
    return parse_frontmatter(content), content[end + 4:]


def as_list(value) -> list:
    if value in ("", None):
        return []
    return value if isinstance(value, list) else [value]


def scalar(value, quote: bool = False) -> str:
    if isinstance(value, int):
        return str(value)
    text = str(value)
    must_quote = quote or text == "" or bool(re.search(r'[:\[\]{}#,&*!|>\'"%@`]', text))
    if must_quote:
        return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return text


def emit_field(key: str, value) -> str:
    if key in LIST_KEYS:
        items = ", ".join(scalar(v) for v in as_list(value))
        return f"{key}: [{items}]"
    return f"{key}: {scalar(value, quote=key in QUOTE_KEYS)}"


def build_page(fm: dict, body: str) -> str:
    keys = [k for k in FIELD_ORDER if k in fm] + [k for k in fm if k not in FIELD_ORDER]
    lines = ["---"] + [emit_field(k, fm[k]) for k in keys] + ["---"]
    return "\n".join(lines) + body


def normalize_milestone(value: str) -> str:
    if not value:
        return ""
    if value.startswith("[["):
        return value
    return f"[[{value}]]"


def load_requirement(req_id: str) -> tuple[Path, dict, str]:
    path = req_path(req_id)
    if not path.exists():
        raise FileNotFoundError(f"requirement not found: {path.relative_to(REPO_ROOT)}")
    fm, body = split_frontmatter(read_file(path))
    return path, fm, body


def append_req_log(body: str, line: str) -> str:
    entry = f"- {today()} {line}"
    heading = "## Status / Schedule Log"
    if heading not in body:
        return body.rstrip() + f"\n\n{heading}\n{entry}\n"

    pattern = rf"({re.escape(heading)}\n)(.*?)(\n## |\Z)"
    match = re.search(pattern, body, flags=re.DOTALL)
    if not match:
        return body.rstrip() + f"\n{entry}\n"
    section = match.group(2).rstrip()
    updated_section = (section + "\n" + entry).lstrip()
    return body[:match.start(2)] + updated_section + body[match.start(3):]


def append_global_log(title: str, detail: str):
    entry = f"## [{today()}] update | {title}\n\n{detail}"
    existing = read_file(LOG_FILE).rstrip()
    LOG_FILE.write_text(existing + "\n\n" + entry + "\n", encoding="utf-8")


def req_link(req_id: str) -> str:
    return f"[[{req_id.upper()}]]"


def sync_scope(fm: dict):
    wbs = str(fm.get("wbs_id", "")).strip()
    rid = str(fm.get("id", "")).strip()
    if not wbs or not rid or not SCOPE_FILE.exists():
        return

    content = read_file(SCOPE_FILE)
    title = str(fm.get("title", rid)).strip()
    owner = str(fm.get("owner", "")).strip()
    start = str(fm.get("start_date", "")).strip()
    due = str(fm.get("due_date", "")).strip()
    status = str(fm.get("status", "")).strip()
    progress = str(fm.get("progress", 0)).strip()
    row = f"| {wbs} | {title} | {req_link(rid)} | {owner} | {start} | {due} | {status} | {progress}% |"

    lines = content.splitlines()
    in_table = False
    insert_at = None
    replaced = False
    for i, line in enumerate(lines):
        if line.startswith("## WBS "):
            in_table = True
            continue
        if in_table and line.startswith("## "):
            insert_at = i
            break
        if in_table and line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) >= 3 and (cells[0] == wbs or req_link(rid) in cells[2]):
                # Skip the table header and separator.
                if cells[0].lower() != "wbs" and set(cells[0]) != {"-"}:
                    lines[i] = row
                    replaced = True
    if not replaced:
        if insert_at is None:
            insert_at = len(lines)
        while insert_at > 0 and lines[insert_at - 1] == "":
            insert_at -= 1
        lines.insert(insert_at, row)

    SCOPE_FILE.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def save_requirement(path: Path, fm: dict, body: str, log_line: str, global_detail: str):
    fm["last_updated"] = today()
    path.write_text(build_page(fm, append_req_log(body, log_line)), encoding="utf-8")
    sync_scope(fm)
    append_global_log(f"{fm.get('id', path.stem)} {log_line}", global_detail)
    print(f"Updated: {path.relative_to(REPO_ROOT)}")


def cmd_approve(args):
    path, fm, body = load_requirement(args.req_id)
    fm["status"] = "approved"
    if args.owner:
        fm["owner"] = args.owner
    if args.assignees is not None:
        fm["assignees"] = [a.strip() for a in args.assignees.split(",") if a.strip()]
    if args.start_date:
        fm["start_date"] = args.start_date
    if args.due_date:
        fm["due_date"] = args.due_date
    if args.wbs_id:
        fm["wbs_id"] = args.wbs_id
    if args.milestone:
        fm["milestone"] = normalize_milestone(args.milestone)
    fm.setdefault("progress", 0)
    decision = f" ({normalize_milestone(args.decision)})" if args.decision else ""
    save_requirement(
        path, fm, body,
        f"approved{decision}",
        f"Approved {fm.get('id')} with owner `{fm.get('owner', '')}`, WBS `{fm.get('wbs_id', '')}`, due `{fm.get('due_date', '')}`.",
    )


def cmd_progress(args):
    path, fm, body = load_requirement(args.req_id)
    if args.progress is not None:
        if not (0 <= args.progress <= 100):
            raise ValueError("--progress must be between 0 and 100")
        fm["progress"] = args.progress
    if args.status:
        if args.status not in ACTIVE_STATUSES | DONE_STATUSES:
            raise ValueError("--status must be in-progress, implemented, verified, or closed")
        fm["status"] = args.status
    note = f" - {args.note}" if args.note else ""
    save_requirement(
        path, fm, body,
        f"progress {fm.get('progress', 0)}%, status {fm.get('status', '')}{note}",
        f"Updated {fm.get('id')} to {fm.get('progress', 0)}% / `{fm.get('status', '')}`.",
    )


def cmd_complete(args):
    path, fm, body = load_requirement(args.req_id)
    fm["status"] = args.status
    fm["progress"] = 100
    fm["completed_date"] = args.completed_date or today()
    decision = f" ({normalize_milestone(args.decision)})" if args.decision else ""
    save_requirement(
        path, fm, body,
        f"completed as {args.status}{decision}",
        f"Completed {fm.get('id')} as `{args.status}` on `{fm.get('completed_date')}`.",
    )


def cmd_drop(args):
    path, fm, body = load_requirement(args.req_id)
    fm["status"] = args.status
    fm["dropped_date"] = args.dropped_date or today()
    fm["dropped_reason"] = args.reason
    save_requirement(
        path, fm, body,
        f"dropped as {args.status} - {args.reason}",
        f"Dropped {fm.get('id')} as `{args.status}` on `{fm.get('dropped_date')}`. Reason: {args.reason}",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Update Project Wiki requirement lifecycle fields")
    sub = parser.add_subparsers(dest="command", required=True)

    approve = sub.add_parser("approve", help="Approve a proposed requirement and set execution fields")
    approve.add_argument("req_id")
    approve.add_argument("--owner")
    approve.add_argument("--assignees", help="Comma-separated assignee names")
    approve.add_argument("--start-date")
    approve.add_argument("--due-date")
    approve.add_argument("--wbs-id")
    approve.add_argument("--milestone")
    approve.add_argument("--decision", help="Decision id such as DEC-003")
    approve.set_defaults(func=cmd_approve)

    progress = sub.add_parser("progress", help="Update requirement progress/status")
    progress.add_argument("req_id")
    progress.add_argument("--progress", type=int)
    progress.add_argument("--status", choices=["in-progress", "implemented", "verified", "closed"])
    progress.add_argument("--note")
    progress.set_defaults(func=cmd_progress)

    complete = sub.add_parser("complete", help="Mark a requirement verified or closed")
    complete.add_argument("req_id")
    complete.add_argument("--status", choices=sorted(DONE_STATUSES), default="verified")
    complete.add_argument("--completed-date")
    complete.add_argument("--decision")
    complete.set_defaults(func=cmd_complete)

    drop = sub.add_parser("drop", help="Reject or defer a requirement")
    drop.add_argument("req_id")
    drop.add_argument("--status", choices=sorted(DROPPED_STATUSES), default="deferred")
    drop.add_argument("--reason", required=True)
    drop.add_argument("--dropped-date")
    drop.set_defaults(func=cmd_drop)
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
