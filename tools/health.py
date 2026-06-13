#!/usr/bin/env python3
from __future__ import annotations

"""
Structural health checks for the Project Management Wiki.

Unlike lint.py (which includes expensive LLM-powered semantic analysis),
health.py is purely deterministic — zero API calls, fast enough to run
every session.

Usage:
    python tools/health.py              # print report to stdout
    python tools/health.py --save       # also save to wiki/health-report.md
    python tools/health.py --json       # machine-readable output

Checks:
  - Empty / stub files (pages with no real content beyond frontmatter)
  - Index sync (wiki/index.md entries vs actual files on disk)
  - Log coverage (interview pages without a corresponding ingest log entry)
  - Requirement schema (valid status/priority enums, unique ids)
  - Traceability (requirements with no source_interviews)
  - Execution gaps (approved+ missing owner/dates; progress range;
    verified/closed not at 100%; rejected/deferred missing drop date/reason)
  - Secret scan (API keys / tokens / obvious PII patterns)

Design boundary (see CLAUDE.md):
  health.py = structural integrity, deterministic, run every session
  status.py = progress / completion / overdue rollup, deterministic
  lint.py   = content quality, semantic (LLM), run every 10-15 ingests
"""

import re
import sys
import json
import argparse
from pathlib import Path
from datetime import date

REPO_ROOT = Path(__file__).parent.parent
WIKI_DIR = REPO_ROOT / "wiki"
INDEX_FILE = WIKI_DIR / "index.md"
LOG_FILE = WIKI_DIR / "log.md"

# Minimum content length (excluding frontmatter) to not be considered a stub
STUB_THRESHOLD_CHARS = 100

VALID_STATUS = {
    "proposed", "approved", "in-progress", "implemented",
    "verified", "closed", "rejected", "deferred",
}
VALID_PRIORITY = {"must", "should", "could", "wont"}
# Statuses where execution/WBS fields are expected to be filled
ACTIVE_STATUS = {"approved", "in-progress", "implemented"}
DONE_STATUS = {"verified", "closed"}
DROPPED_STATUS = {"rejected", "deferred"}

# Directories / files that are not real wiki pages
EXCLUDE_NAMES = {"index.md", "log.md", "lint-report.md", "health-report.md", "tags.md"}
EXCLUDE_DIRS = {"_templates"}

# High-confidence secret patterns + a couple of obvious PII patterns
SECRET_PATTERNS = [
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("OpenAI-style key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    ("Private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("Generic secret assignment",
     re.compile(r"(?i)(api[_-]?key|secret|token|passwd|password)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}")),
    ("Korean RRN (PII)", re.compile(r"\b\d{6}-[1-4]\d{6}\b")),
    ("Credit-card-like (PII)", re.compile(r"\b(?:\d[ -]?){13,16}\b")),
]


def read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def all_wiki_pages() -> list[Path]:
    """All .md files in wiki/, excluding meta files and template dir."""
    return [
        p for p in WIKI_DIR.rglob("*.md")
        if p.name not in EXCLUDE_NAMES
        and not any(part in EXCLUDE_DIRS for part in p.relative_to(WIKI_DIR).parts)
    ]


def strip_frontmatter(content: str) -> str:
    """Remove YAML frontmatter (--- ... ---) from content."""
    if content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            return content[end + 3:].strip()
    return content.strip()


def parse_frontmatter(content: str) -> dict:
    """Minimal YAML-frontmatter parser for the flat key: value (+ inline list)
    schema this wiki uses. No external deps. Handles:
        key: scalar
        key: "quoted scalar"
        key: [a, b, c]        # inline list
        key:                  # block list
          - a
          - b
    """
    if not content.startswith("---"):
        return {}
    end = content.find("\n---", 3)
    if end == -1:
        return {}
    block = content[3:end].strip("\n")

    data: dict = {}
    pending_key: str | None = None
    for line in block.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        # block-list item
        m = re.match(r"\s*-\s+(.*)$", line)
        if m and pending_key is not None:
            data.setdefault(pending_key, [])
            if isinstance(data[pending_key], list):
                data[pending_key].append(_scalar(m.group(1)))
            continue
        m = re.match(r"([A-Za-z_][\w-]*):\s*(.*)$", line)
        if not m:
            continue
        key, raw = m.group(1), m.group(2).strip()
        if raw == "":
            pending_key = key
            data[key] = []  # may stay empty or be filled by block list
            continue
        pending_key = None
        if raw.startswith("[") and raw.endswith("]"):
            inner = raw[1:-1].strip()
            data[key] = [_scalar(x) for x in inner.split(",")] if inner else []
        else:
            data[key] = _scalar(raw)
    return data


def _scalar(raw: str):
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == raw[-1] == '"':
        return raw[1:-1].replace(r"\"", '"')
    if len(raw) >= 2 and raw[0] == raw[-1] == "'":
        return raw[1:-1]
    if re.fullmatch(r"-?\d+", raw):
        return int(raw)
    return raw


# ── Check: Empty / Stub files ───────────────────────────────────────

def check_empty_files(pages: list[Path], threshold: int = STUB_THRESHOLD_CHARS) -> list[dict]:
    """Find wiki pages that are empty or contain only frontmatter / minimal content."""
    results = []
    for p in pages:
        raw = read_file(p)
        body = strip_frontmatter(raw)
        if len(body) < threshold:
            results.append({
                "path": str(p.relative_to(REPO_ROOT)),
                "total_bytes": len(raw),
                "body_bytes": len(body),
                "status": "empty" if len(body) == 0 else "stub",
            })
    results.sort(key=lambda x: x["body_bytes"])
    return results


# ── Check: Index sync ───────────────────────────────────────────────

def _parse_index_links(index_content: str) -> set[str]:
    """Extract markdown link targets from index.md."""
    return set(re.findall(r'\[.*?\]\(([^)]+\.md)\)', index_content))


def check_index_sync(pages: list[Path]) -> dict:
    """Compare wiki/index.md entries against actual files on disk."""
    index_content = read_file(INDEX_FILE)
    index_links = _parse_index_links(index_content)

    # overview.md / charter.md are listed under ## Project, scope under its own
    # link; meta-ish pages are excluded from the strict cross-check.
    meta_pages = {"overview.md", "charter.md"}

    index_paths = set()
    for link in index_links:
        resolved = (WIKI_DIR / link).resolve()
        if Path(link).name not in meta_pages:
            index_paths.add(resolved)

    disk_paths = set()
    for p in pages:
        if p.name not in meta_pages:
            disk_paths.add(p.resolve())

    in_index_not_on_disk = [
        str(p.relative_to(REPO_ROOT)) for p in sorted(index_paths - disk_paths)
        if REPO_ROOT in p.parents or p == REPO_ROOT
    ]
    on_disk_not_in_index = [
        str(p.relative_to(REPO_ROOT)) for p in sorted(disk_paths - index_paths)
    ]

    return {
        "in_index_not_on_disk": in_index_not_on_disk,
        "on_disk_not_in_index": on_disk_not_in_index,
    }


# ── Check: Log coverage (interviews) ────────────────────────────────

def _parse_log_entries(log_content: str) -> set[str]:
    """Extract titles from ingest log entries (## [date] ingest | Title)."""
    return set(
        m.group(1).strip().lower()
        for m in re.finditer(r'^## \[\d{4}-\d{2}-\d{2}\] ingest \| (.+)$', log_content, re.MULTILINE)
    )


def check_log_coverage(pages: list[Path]) -> list[dict]:
    """Find interview pages with no corresponding ingest entry in log.md."""
    log_content = read_file(LOG_FILE)
    logged_titles = _parse_log_entries(log_content)

    interview_dir = WIKI_DIR / "interviews"
    if not interview_dir.exists():
        return []

    missing = []
    for p in sorted(interview_dir.glob("*.md")):
        slug = p.stem.lower().replace("-", " ").replace("_", " ")
        fm = parse_frontmatter(read_file(p))
        fm_title = str(fm.get("title", "")).strip().lower()
        if slug not in logged_titles and fm_title not in logged_titles:
            missing.append({
                "path": str(p.relative_to(REPO_ROOT)),
                "slug": p.stem,
                "title": fm_title or p.stem,
            })
    return missing


# ── Check: Requirement schema & execution ──────────────────────────

def _requirement_pages() -> list[Path]:
    req_dir = WIKI_DIR / "requirements"
    return sorted(req_dir.glob("*.md")) if req_dir.exists() else []


def check_requirements() -> dict:
    """Validate requirement frontmatter: enums, unique ids, traceability,
    execution-field completeness, and completion/drop consistency."""
    issues: list[dict] = []
    seen_ids: dict[str, str] = {}

    def add(path: Path, kind: str, msg: str):
        issues.append({"path": str(path.relative_to(REPO_ROOT)), "kind": kind, "message": msg})

    for p in _requirement_pages():
        fm = parse_frontmatter(read_file(p))
        rid = str(fm.get("id", "")).strip()
        status = str(fm.get("status", "")).strip()
        priority = str(fm.get("priority", "")).strip()

        if not rid:
            add(p, "missing-id", "no `id` in frontmatter")
        elif rid in seen_ids:
            add(p, "duplicate-id", f"id `{rid}` also used by `{seen_ids[rid]}`")
        else:
            seen_ids[rid] = str(p.relative_to(REPO_ROOT))

        if status not in VALID_STATUS:
            add(p, "bad-status", f"invalid status `{status or '(empty)'}`")
        if priority not in VALID_PRIORITY:
            add(p, "bad-priority", f"invalid priority `{priority or '(empty)'}`")

        # Traceability: every requirement should cite a source interview
        srcs = fm.get("source_interviews") or []
        if not srcs:
            add(p, "orphan", "no `source_interviews` (untraceable requirement)")

        # progress range
        progress = fm.get("progress", 0)
        try:
            progress = int(progress)
        except (TypeError, ValueError):
            progress = -1
        if not (0 <= progress <= 100):
            add(p, "bad-progress", f"progress `{fm.get('progress')}` out of 0–100")

        # execution gaps for active requirements
        if status in ACTIVE_STATUS:
            if not str(fm.get("owner", "")).strip():
                add(p, "exec-gap", f"status `{status}` but no owner")
            if not str(fm.get("start_date", "")).strip() or not str(fm.get("due_date", "")).strip():
                add(p, "exec-gap", f"status `{status}` but start_date/due_date missing")

        # completion consistency
        if status in DONE_STATUS:
            if progress != 100:
                add(p, "done-mismatch", f"status `{status}` but progress {progress} (expected 100)")
            if not str(fm.get("completed_date", "")).strip():
                add(p, "done-mismatch", f"status `{status}` but no completed_date")

        # drop consistency
        if status in DROPPED_STATUS:
            if not str(fm.get("dropped_date", "")).strip():
                add(p, "drop-mismatch", f"status `{status}` but no dropped_date")
            if not str(fm.get("dropped_reason", "")).strip():
                add(p, "drop-mismatch", f"status `{status}` but no dropped_reason")

    return {"count": len(_requirement_pages()), "issues": issues}


# ── Check: Secret / PII scan ────────────────────────────────────────

def check_secrets(pages: list[Path]) -> list[dict]:
    """Scan page text for high-confidence secrets and obvious PII patterns."""
    findings = []
    for p in pages:
        text = read_file(p)
        for lineno, line in enumerate(text.splitlines(), 1):
            for label, pat in SECRET_PATTERNS:
                if pat.search(line):
                    findings.append({
                        "path": str(p.relative_to(REPO_ROOT)),
                        "line": lineno,
                        "type": label,
                    })
    return findings


# ── Report Generation ───────────────────────────────────────────────

def run_health() -> dict:
    """Run all health checks, return structured results."""
    pages = all_wiki_pages()
    return {
        "date": date.today().isoformat(),
        "total_pages": len(pages),
        "empty_files": check_empty_files(pages),
        "index_sync": check_index_sync(pages),
        "log_coverage": check_log_coverage(pages),
        "requirements": check_requirements(),
        "secrets": check_secrets(pages),
    }


def format_report(results: dict) -> str:
    """Format health check results as markdown."""
    lines = [
        f"# Project Wiki Health Report — {results['date']}",
        "",
        f"Scanned {results['total_pages']} wiki pages. "
        "Checks are purely structural (no LLM calls).",
        "",
    ]

    # ── Empty / Stub Files
    empty = results["empty_files"]
    lines.append(f"## Empty / Stub Files ({len(empty)} found)")
    lines.append("")
    if empty:
        lines.append("| Page | Total Bytes | Body Bytes | Status |")
        lines.append("|---|---|---|---|")
        for ef in empty:
            emoji = "🔴" if ef["status"] == "empty" else "🟡"
            lines.append(f"| `{ef['path']}` | {ef['total_bytes']} | {ef['body_bytes']} | {emoji} {ef['status']} |")
    else:
        lines.append("All pages have content beyond frontmatter. ✅")
    lines.append("")

    # ── Index Sync
    isync = results["index_sync"]
    stale = isync["in_index_not_on_disk"]
    missing = isync["on_disk_not_in_index"]
    total_issues = len(stale) + len(missing)
    lines.append(f"## Index Sync ({total_issues} issues)")
    lines.append("")
    if stale:
        lines.append("### Stale Index Entries (in index.md but no file on disk)")
        for s in stale:
            lines.append(f"- `{s}`")
        lines.append("")
    if missing:
        lines.append("### Missing from Index (file exists but not in index.md)")
        for m in missing:
            lines.append(f"- `{m}`")
        lines.append("")
    if not stale and not missing:
        lines.append("index.md is in sync with disk. ✅")
        lines.append("")

    # ── Log Coverage
    log_missing = results["log_coverage"]
    lines.append(f"## Log Coverage ({len(log_missing)} interviews without log entry)")
    lines.append("")
    if log_missing:
        lines.append("These interview pages have no corresponding `ingest` entry in log.md:")
        lines.append("")
        for lm in log_missing:
            lines.append(f"- `{lm['path']}` — {lm['title']}")
    else:
        lines.append("All interview pages have corresponding log entries. ✅")
    lines.append("")

    # ── Requirements
    reqs = results["requirements"]
    rissues = reqs["issues"]
    lines.append(f"## Requirement Schema & Execution ({len(rissues)} issues across {reqs['count']} requirements)")
    lines.append("")
    if rissues:
        lines.append("| Page | Kind | Issue |")
        lines.append("|---|---|---|")
        for it in rissues:
            lines.append(f"| `{it['path']}` | {it['kind']} | {it['message']} |")
    else:
        lines.append("All requirements pass schema, traceability, and execution checks. ✅")
    lines.append("")

    # ── Secrets / PII
    secrets = results["secrets"]
    lines.append(f"## Secret / PII Scan ({len(secrets)} findings)")
    lines.append("")
    if secrets:
        lines.append("⚠️ Potential secrets or PII found — review and remove/pseudonymize before committing:")
        lines.append("")
        lines.append("| Page | Line | Type |")
        lines.append("|---|---|---|")
        for s in secrets:
            lines.append(f"| `{s['path']}` | {s['line']} | {s['type']} |")
    else:
        lines.append("No secrets or obvious PII patterns detected. ✅")
    lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Structural health checks for the Project Wiki (deterministic, no LLM calls)"
    )
    parser.add_argument("--save", action="store_true",
                        help="Save report to wiki/health-report.md")
    parser.add_argument("--json", action="store_true",
                        help="Output machine-readable JSON instead of markdown")
    args = parser.parse_args()

    results = run_health()

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        report = format_report(results)
        print(report)
        if args.save:
            report_path = WIKI_DIR / "health-report.md"
            report_path.write_text(report, encoding="utf-8")
            print(f"\nSaved: {report_path.relative_to(REPO_ROOT)}")
