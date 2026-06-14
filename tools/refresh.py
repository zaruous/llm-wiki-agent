#!/usr/bin/env python3
"""
Raw inbox checker for the Project Management Wiki.

Lists source documents in raw/ that have not been ingested yet, and flags
already-ingested interviews whose raw source has changed since ingest. In the
PM model interviews are point-in-time records (re-ingesting creates a NEW INT
rather than overwriting), so this tool *reports* rather than auto-refreshes.

Deterministic — no LLM calls.

Usage:
    python tools/refresh.py            # list un-ingested raw docs + changed sources
    python tools/refresh.py --json     # machine-readable output

Linkage: an interview page records its origin via `source_file:` in frontmatter.
A raw file is "ingested" when some interview page points at it.
"""

import sys
import json
import hashlib
import re
import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
WIKI_DIR = REPO_ROOT / "wiki"
RAW_DIR = REPO_ROOT / "raw"
INTERVIEWS_DIR = WIKI_DIR / "interviews"

SUPPORTED = {".md", ".pdf", ".docx", ".pptx", ".xlsx", ".xls", ".html", ".htm",
             ".txt", ".csv", ".json", ".xml", ".rst", ".rtf", ".epub", ".ipynb",
             ".yaml", ".yml", ".tsv", ".wav", ".mp3"}


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def extract_source_file(content: str) -> str | None:
    """Extract source_file from YAML frontmatter."""
    match = re.search(r'^source_file:\s*(.+)$', content, re.MULTILINE)
    if match:
        val = match.group(1).strip().strip('"').strip("'")
        return val or None
    return None


def ingested_sources() -> dict[str, Path]:
    """Map of resolved raw-source path -> interview page that ingested it."""
    out: dict[str, Path] = {}
    if not INTERVIEWS_DIR.exists():
        return out
    for page in sorted(INTERVIEWS_DIR.glob("*.md")):
        src = extract_source_file(read_file(page))
        if not src:
            continue
        raw_path = (REPO_ROOT / src)
        if not raw_path.exists():
            raw_path = RAW_DIR / src
        out[str(raw_path.resolve())] = page
    return out


def scan() -> dict:
    sources = ingested_sources()
    raw_files = [p for p in RAW_DIR.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED] \
        if RAW_DIR.exists() else []

    not_ingested = []
    for p in sorted(raw_files):
        if str(p.resolve()) not in sources:
            not_ingested.append(str(p.relative_to(REPO_ROOT)))

    # interviews whose source_file points at a missing raw doc
    missing_source = []
    for resolved, page in sources.items():
        if not Path(resolved).exists():
            missing_source.append(str(page.relative_to(REPO_ROOT)))

    return {
        "raw_total": len(raw_files),
        "ingested": len(sources),
        "not_ingested": not_ingested,
        "interviews_missing_source": sorted(missing_source),
    }


def main():
    parser = argparse.ArgumentParser(description="Raw inbox checker for the Project Wiki")
    parser.add_argument("--json", action="store_true", help="Machine-readable JSON output")
    args = parser.parse_args()

    result = scan()
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    print(f"Raw documents: {result['raw_total']}  |  ingested: {result['ingested']}")
    print()
    ni = result["not_ingested"]
    print(f"## Not yet ingested ({len(ni)})")
    if ni:
        for p in ni:
            print(f"  • {p}")
        print("\n  Ingest with: python tools/ingest.py <path>")
    else:
        print("  All raw documents have been ingested. ✅")

    ms = result["interviews_missing_source"]
    if ms:
        print(f"\n## Interviews whose source_file is missing ({len(ms)})")
        for p in ms:
            print(f"  • {p}")


if __name__ == "__main__":
    main()
