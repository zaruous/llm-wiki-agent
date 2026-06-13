#!/usr/bin/env python3
from __future__ import annotations

"""
Frontmatter formatter & tag linter for the Project Management Wiki.

Deterministic — zero LLM calls. Normalizes YAML frontmatter to a canonical field
order per page type, coerces field types (progress→int, tags→kebab-case, deduped
and sorted), and validates tags against the controlled vocabulary in
`wiki/tags.md`. Unknown tags are reported, never auto-deleted.

Usage:
    python tools/format.py             # check only — report what would change
    python tools/format.py --write     # apply normalization in place
    python tools/format.py --json      # machine-readable report

Boundary:
    health.py  = structural integrity (schema enums, traceability, secrets)
    format.py  = frontmatter style/normalization + tag vocabulary
    status.py  = progress / completion rollup
"""

import re
import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from health import REPO_ROOT, WIKI_DIR, read_file, parse_frontmatter  # noqa: E402

TAGS_FILE = WIKI_DIR / "tags.md"

EXCLUDE_NAMES = {"index.md", "log.md", "lint-report.md", "health-report.md", "tags.md"}
EXCLUDE_DIRS = {"_templates"}

# Canonical field order per page type.
CANON = {
    "requirement": ["id", "title", "type", "category", "priority", "status",
                    "source_interviews", "wbs_id", "owner", "assignees", "progress",
                    "start_date", "due_date", "completed_date", "dropped_date",
                    "dropped_reason", "depends_on", "milestone", "tags", "last_updated"],
    "interview": ["id", "title", "type", "interview_type", "date", "participants",
                  "source_file", "tags", "last_updated"],
    "decision": ["id", "title", "type", "date", "tags", "last_updated"],
    "stakeholder": ["title", "type", "role", "influence", "tags", "last_updated"],
    "milestone": ["id", "title", "type", "target_date", "status", "tags", "last_updated"],
    "risk": ["id", "title", "type", "probability", "impact", "status", "tags", "last_updated"],
    "scope": ["title", "type", "tags", "last_updated"],
    "charter": ["title", "type", "tags", "last_updated"],
    "synthesis": ["id", "title", "type", "tags", "last_updated"],
}

# Minimum required fields per type (key must be present).
REQUIRED = {
    "requirement": ["id", "title", "type", "category", "priority", "status",
                    "source_interviews", "tags", "last_updated"],
    "interview": ["id", "title", "type", "date", "tags", "last_updated"],
    "decision": ["id", "title", "type", "tags", "last_updated"],
    "milestone": ["id", "title", "type", "target_date", "tags", "last_updated"],
    "risk": ["id", "title", "type", "tags", "last_updated"],
}
DEFAULT_REQUIRED = ["title", "type", "tags", "last_updated"]

ALWAYS_QUOTE_KEYS = {"title", "dropped_reason", "source_file", "role"}
LIST_KEYS = {"source_interviews", "assignees", "participants", "depends_on", "tags"}


# ── page collection ─────────────────────────────────────────────────

def all_wiki_pages() -> list[Path]:
    return [p for p in WIKI_DIR.rglob("*.md")
            if p.name not in EXCLUDE_NAMES
            and not any(part in EXCLUDE_DIRS for part in p.relative_to(WIKI_DIR).parts)]


# ── tag registry ────────────────────────────────────────────────────

def load_tag_registry() -> tuple[set[str], list[str]]:
    text = read_file(TAGS_FILE)
    allowed: set[str] = set()
    namespaces: list[str] = []
    for m in re.finditer(r'^- `?([^\s`]+)`?', text, re.MULTILINE):
        tok = m.group(1)
        if tok.endswith("/"):
            namespaces.append(tok)
        else:
            allowed.add(tok.lower())
    return allowed, namespaces


def is_valid_tag(tag: str, allowed: set[str], namespaces: list[str]) -> bool:
    return tag in allowed or any(tag.startswith(ns) for ns in namespaces)


def normalize_tag(tag) -> str:
    return str(tag).strip().lower().replace(" ", "-")


# ── frontmatter split / emit ────────────────────────────────────────

def split_frontmatter(content: str):
    """Return (fm_dict, body_after_closing, ok). body includes its leading newline."""
    if not content.startswith("---"):
        return None, content, False
    end = content.find("\n---", 3)
    if end == -1:
        return None, content, False
    fm = parse_frontmatter(content)
    body = content[end + 4:]  # text after the closing '---'
    return fm, body, True


def _needs_quote(s: str) -> bool:
    if s == "":
        return True
    if s != s.strip():
        return True
    return bool(re.search(r'[:\[\]{}#,&*!|>\'"%@`]', s)) or s[0] in "-?"


def emit_scalar(val, force_quote: bool = False) -> str:
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, int):
        return str(val)
    s = str(val)
    if force_quote or _needs_quote(s):
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return s


def emit_field(key: str, val) -> str:
    if isinstance(val, list):
        inner = ", ".join(emit_scalar(x) for x in val)
        return f"{key}: [{inner}]"
    return f"{key}: {emit_scalar(val, force_quote=key in ALWAYS_QUOTE_KEYS)}"


def normalize_fm(fm: dict) -> dict:
    """Return a normalized copy: tags kebab/dedupe/sort, progress int, list keys as lists."""
    out = dict(fm)
    # tags
    if "tags" in out:
        raw = out["tags"] if isinstance(out["tags"], list) else ([out["tags"]] if out["tags"] not in ("", None) else [])
        seen, norm = set(), []
        for t in raw:
            nt = normalize_tag(t)
            if nt and nt not in seen:
                seen.add(nt)
                norm.append(nt)
        out["tags"] = sorted(norm)
    # progress
    if "progress" in out and not isinstance(out["progress"], int):
        try:
            out["progress"] = int(str(out["progress"]).strip())
        except (TypeError, ValueError):
            pass
    # ensure list keys are lists
    for k in LIST_KEYS:
        if k in out and not isinstance(out[k], list):
            out[k] = [] if out[k] in ("", None) else [out[k]]
    return out


def ordered_keys(fm: dict, ptype: str) -> list[str]:
    canon = CANON.get(ptype, list(fm.keys()))
    keys = [k for k in canon if k in fm]
    keys += [k for k in fm if k not in keys]  # preserve extras at the end
    return keys


def build_content(fm: dict, ptype: str, body: str) -> str:
    keys = ordered_keys(fm, ptype)
    lines = ["---"] + [emit_field(k, fm[k]) for k in keys] + ["---"]
    return "\n".join(lines) + body


# ── checks ──────────────────────────────────────────────────────────

def check_page(path: Path, allowed: set[str], namespaces: list[str]) -> dict:
    content = read_file(path)
    fm, body, ok = split_frontmatter(content)
    rel = str(path.relative_to(REPO_ROOT))
    if not ok:
        return {"path": rel, "issues": ["no frontmatter"], "changed": False, "new_content": None}

    ptype = str(fm.get("type", "")).strip()
    issues: list[str] = []

    # required fields
    required = REQUIRED.get(ptype, DEFAULT_REQUIRED)
    for f in required:
        if f not in fm:
            issues.append(f"missing required field `{f}`")

    # unknown tags (against normalized form)
    norm = normalize_fm(fm)
    for t in norm.get("tags", []):
        if not is_valid_tag(t, allowed, namespaces):
            issues.append(f"unknown tag `{t}` (not in wiki/tags.md)")

    # tag normalization needed?
    orig_tags = fm.get("tags", [])
    orig_tags = orig_tags if isinstance(orig_tags, list) else ([orig_tags] if orig_tags not in ("", None) else [])
    if [str(t) for t in orig_tags] != norm.get("tags", []):
        issues.append("tags not normalized (case/spacing/dupes/order)")

    # field order
    if ptype in CANON:
        present_canon = [k for k in fm if k in CANON[ptype]]
        expected = [k for k in CANON[ptype] if k in fm]
        if present_canon != expected:
            issues.append("fields out of canonical order")

    # progress type
    if "progress" in fm and not isinstance(fm["progress"], int):
        issues.append("progress is not an integer")

    new_content = build_content(norm, ptype, body)
    changed = new_content != content
    return {"path": rel, "issues": issues, "changed": changed, "new_content": new_content}


def run(write: bool = False) -> dict:
    allowed, namespaces = load_tag_registry()
    results = []
    for p in sorted(all_wiki_pages()):
        r = check_page(p, allowed, namespaces)
        if write and r["changed"] and r["new_content"] is not None:
            Path(REPO_ROOT / r["path"]).write_text(r["new_content"], encoding="utf-8")
            r["written"] = True
        results.append(r)
    return {
        "checked": len(results),
        "with_issues": [r for r in results if r["issues"]],
        "would_change": [r["path"] for r in results if r["changed"]],
        "results": results,
    }


def format_report(report: dict, wrote: bool) -> str:
    lines = [f"# Frontmatter Format & Tag Report", "",
             f"Checked {report['checked']} pages.", ""]
    issues = report["with_issues"]
    lines.append(f"## Issues ({len(issues)} pages)")
    if issues:
        for r in issues:
            lines.append(f"- `{r['path']}`")
            for it in r["issues"]:
                lines.append(f"    - {it}")
    else:
        lines.append("No frontmatter or tag issues. ✅")
    lines.append("")
    changed = report["would_change"]
    verb = "Reformatted" if wrote else "Would reformat"
    lines.append(f"## {verb} ({len(changed)} pages)")
    if changed:
        for p in changed:
            lines.append(f"- `{p}`")
        if not wrote:
            lines.append("\nRun `python tools/format.py --write` to apply.")
    else:
        lines.append("All pages already canonically formatted. ✅")
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Frontmatter formatter & tag linter (deterministic)")
    parser.add_argument("--write", action="store_true", help="Apply normalization in place")
    parser.add_argument("--json", action="store_true", help="Machine-readable JSON output")
    args = parser.parse_args()

    report = run(write=args.write)
    if args.json:
        # drop bulky new_content from JSON
        for r in report["results"]:
            r.pop("new_content", None)
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(format_report(report, wrote=args.write))
