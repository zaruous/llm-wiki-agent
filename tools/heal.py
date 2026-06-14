#!/usr/bin/env python3
"""
Wiki Self-Healing Tool (project management wiki)

Finds names referenced via [[wikilink]] in 3+ pages but lacking their own page
(typically a stakeholder mentioned everywhere but never created) and generates a
clearly-marked STUB stakeholder page for each, grounded in where the name appears.

The output is a STUB for human review — never an authoritative record. This tool
only creates pages; it never deletes or rewrites existing ones.

Usage:
    python tools/heal.py
"""

import os
import sys
from pathlib import Path

try:
    from litellm import completion
except ImportError:
    print("Error: litellm not installed. Run: pip install litellm")
    sys.exit(1)

# Ensure tools can be imported
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.lint import find_missing_pages, all_wiki_pages

REPO_ROOT = Path(__file__).parent.parent
WIKI_DIR = REPO_ROOT / "wiki"
STAKEHOLDERS_DIR = WIKI_DIR / "stakeholders"


def call_llm(prompt: str, max_tokens: int = 1200) -> str:
    # Uses litellm standard env vars (ANTHROPIC_API_KEY, etc.)
    model = os.getenv("LLM_MODEL", "claude-3-5-haiku-latest")  # default to fast model
    response = completion(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content


def search_mentions(name: str, pages: list[Path]) -> list[Path]:
    """Find up to 15 pages where this name is mentioned (excluding generated dirs)."""
    found = []
    for p in pages:
        if "stakeholders" not in str(p.parent):
            content = p.read_text(encoding="utf-8")
            if name.lower() in content.lower():
                found.append(p)
    return found[:15]


def heal_missing_pages():
    pages = all_wiki_pages()
    missing = find_missing_pages(pages)

    if not missing:
        print("No missing pages. Every name referenced 3+ times already has a page.")
        return

    STAKEHOLDERS_DIR.mkdir(exist_ok=True, parents=True)
    print(f"Found {len(missing)} names referenced 3+ times without a page. "
          "Generating STUB stakeholder pages for review...")

    for name in missing:
        out_path = STAKEHOLDERS_DIR / f"{name}.md"
        if out_path.exists():
            print(f" -> Skipping {name}: page already exists")
            continue

        print(f"Drafting stub for: {name}")
        mentions = search_mentions(name, pages)
        context = ""
        for s in mentions:
            context += f"\n\n### {s.relative_to(WIKI_DIR)}\n{s.read_text(encoding='utf-8')[:800]}"

        prompt = f"""You are drafting a STUB stakeholder page for a project management wiki.
The name "{name}" is referenced in several pages but has no page of its own.

Here is how "{name}" appears in the current wiki:
{context}

Produce ONLY a markdown page in exactly this format (infer role from context; leave
unknowns blank). Mark it clearly as a stub for human review:
---
title: "{name}"
type: stakeholder
role: ""
influence: med
tags: [stub]
last_updated: ""
---

> **STUB — needs human review.** Auto-drafted from mentions; verify before relying on it.

## Role
(infer from context, or leave a question)

## Interests

## Influence

## Related
(list the [[pages]] where this name appears)
"""
        try:
            result = call_llm(prompt)
            out_path.write_text(result, encoding="utf-8")
            print(f" -> Saved STUB to {out_path.relative_to(REPO_ROOT)} (review and complete it)")
        except Exception as e:
            print(f" [!] Failed to generate {name}: {e}")


if __name__ == "__main__":
    heal_missing_pages()
