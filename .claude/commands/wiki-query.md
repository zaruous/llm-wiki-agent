Query the Project Wiki and synthesize an answer.

Usage: /wiki-query $ARGUMENTS

$ARGUMENTS is the question, e.g. `which must requirements are still open or overdue?`

Follow the Query Workflow defined in CLAUDE.md:
1. Read wiki/index.md to identify the most relevant pages
2. Read those pages (up to ~10 most relevant)
3. Support status/priority/owner/date filters — e.g. open `must`, overdue (due_date < today and not verified/closed), by owner, by milestone
4. Synthesize a thorough markdown answer with [[PageName]] wikilink citations
5. Include a ## Sources section listing pages you drew from
6. Ask the user if they want the answer saved as wiki/syntheses/<slug>.md

For pure status/progress/completion numbers, prefer `python tools/status.py`
(deterministic) over reasoning over pages. If the wiki is empty, say so and
suggest running /wiki-ingest first.
