Content-quality lint of the Project Wiki.

Usage: /wiki-lint

Run `python tools/health.py` first (structural checks are cheap). Then follow the
Lint Workflow in CLAUDE.md for the semantic checks (read and reason over pages):

1. Orphan / broken [[wikilinks]]
2. Contradictions — conflicting claims or duplicate/overlapping requirements
3. Missing acceptance criteria — requirements with no DoD
4. Unmapped requirements — approved+ requirements with no WBS tasks / scope mapping
5. Out-of-scope but still active — requirements in Out-of-Scope yet not rejected/deferred
6. Overdue / stalled — past due_date, or progress unchanged for a long time
7. Stale pages — not updated after newer interviews changed the picture
8. Data gaps — questions the wiki can't answer; suggest specific interviews/sources

Output a structured markdown lint report. At the end, ask if the user wants it
saved to wiki/lint-report.md.

Append to wiki/log.md: ## [today's date] lint | Project wiki quality check
