Normalize wiki frontmatter and check tags.

Usage: /wiki-format

Follow the Format & Tags Workflow in CLAUDE.md. Run `python tools/format.py`
(deterministic, no LLM calls):

- `python tools/format.py`          → check only; report what would change
- `python tools/format.py --write`  → apply normalization in place

It normalizes frontmatter to the canonical field order per page type, coerces
types (progress→int; tags→kebab-case, lowercased, de-duplicated, sorted), reports
missing required fields and fields out of order, and validates tags against the
controlled vocabulary in `wiki/tags.md` (unknown tags are reported, never deleted).

After reviewing the report, offer to run `--write`. If unknown tags are
legitimate, add them to `wiki/tags.md` rather than forcing them through.

Append to wiki/log.md: ## [today's date] format | Frontmatter normalized
