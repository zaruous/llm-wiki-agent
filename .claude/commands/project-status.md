Show the project status dashboard.

Usage: /project-status

Follow the Status Workflow in CLAUDE.md. Run `python tools/status.py`
(deterministic rollup, no LLM calls). If Python/deps are unavailable, compute the
same by reading requirement frontmatter across wiki/requirements/:

- Requirement counts by status and by priority (MoSCoW)
- Completion rate = (verified + closed) / (total − rejected − deferred)
- Weighted progress = mean(progress) over active requirements (exclude rejected/deferred)
- Overdue list — active requirements whose due_date is before today
- Exit readiness — all `must` requirements verified/closed AND no overdue AND no open `high` risk AND Exit Criteria met (see wiki/scope/scope.md)

Print the dashboard. Offer to refresh wiki/overview.md with the latest numbers.

Append to wiki/log.md: ## [today's date] status | Project status checked
