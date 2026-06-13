Build the Project Wiki traceability graph.

Usage: /wiki-graph

First try running: python tools/build_graph.py --open

If that fails (missing dependencies), build the graph manually:

1. Use Grep to find all [[wikilinks]] across every file in wiki/
2. Build a nodes list: one node per wiki page, id=relative-path, label=title, type from frontmatter (color by type: requirement / interview / decision / stakeholder / milestone / risk / scope)
3. Build edges: one EXTRACTED edge per [[wikilink]]; add predecessor edges from each requirement's depends_on
4. Infer additional implicit relationships not captured by wikilinks — tag INFERRED with a confidence score (0.0–1.0); low confidence → AMBIGUOUS
5. Highlight broken traceability paths (interview → requirement → scope/WBS that don't connect)
6. Write graph/graph.json with {nodes, edges, built: today}
7. Write graph/graph.html as a self-contained vis.js page (interactive, searchable)

After building, summarize: node/edge counts, breakdown by type, most-connected requirements, and any broken traceability paths found.

Append to wiki/log.md: ## [today's date] graph | Traceability graph rebuilt
