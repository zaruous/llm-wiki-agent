# Project Management Wiki Agent

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**A coding-agent skill for running a project.** Drop interview notes, requirement docs, and meeting records into `raw/` and tell the agent to ingest them — it distills them into tracked **requirements**, keeps owners/dates/progress current, and follows each one through its lifecycle to **done or dropped**, with full traceability from the originating interview to project completion.

> Most PM tools make you fill in the tracker by hand. This one reads your interviews and docs, writes the requirements, wires the traceability, assigns the WBS, and keeps the dashboard current — you just talk to it.

```
ingest raw/interviews/2026-06-13-kickoff.md
approve REQ-012, owner Kim, start 6/16, due 6/27, WBS 1.2.3
update REQ-012 progress to 40%
project status
```

```
wiki/
├── index.md          catalog of all pages — updated on every ingest
├── log.md            append-only record of every operation
├── overview.md       live project dashboard (progress / scope / risks)
├── charter.md        project charter: goal, success criteria, scope, stakeholders
├── requirements/     REQ-XXX — the core artifact (lifecycle + WBS fields)
├── interviews/       INT-XXX — interview & meeting records
├── scope/            scope definition / master WBS / DoD / Exit Criteria
├── decisions/        DEC-XXX — decision records (ADR style)
├── stakeholders/     people, organizations, roles
├── milestones/       M-XXX — milestones / gates
├── risks/            RISK-XXX — risk register
└── syntheses/        saved query answers / analyses
graph/
├── graph.json        persistent node/edge data
└── graph.html        interactive traceability graph — open in any browser
```

## The Core Idea: Traceability

```
Interview (what was said)  →  Requirement (distilled)  →  Scope / WBS (planned)
   →  Execution status & progress  →  Definition of Done (verified / closed)
   INT-001                     REQ-012                     status                completed_date
```

Every requirement records where it came from, the decision that approved it, whether it's in scope, who owns it, its schedule and progress — and, if dropped, **when and why**. From the first interview to project close-out, one wiki.

## Install

**Requires:** [Claude Code](https://claude.ai/code), [Codex](https://openai.com/codex), [Gemini CLI](https://github.com/google-gemini/gemini-cli), or any agent that reads a config file.

```bash
git clone https://github.com/zaruous/llm-wiki-agent.git
cd llm-wiki-agent
```

Open in your agent — no API key or Python setup needed for the conversational workflows:

```bash
claude      # reads CLAUDE.md + .claude/commands/ (slash commands available)
codex       # reads AGENTS.md
opencode    # reads AGENTS.md
gemini      # reads GEMINI.md
```

## Usage

All agents understand natural language and shorthand triggers:

```
ingest raw/interviews/kickoff.md          # interview → INT page + extracted requirements
approve REQ-012, owner Kim, due 6/27       # confirm a requirement, fill WBS fields
update REQ-012 progress to 40%             # track execution
defer REQ-019 — budget hold                # drop with date + reason recorded
query: open must requirements?             # status/priority/owner/date filters
project status                             # completion rate / overdue / exit readiness
lint                                       # contradictions, unmapped reqs, gaps
build graph                                # traceability graph (interview→req→scope)
```

**Claude Code** also provides `/wiki-ingest`, `/wiki-query`, `/wiki-health`, `/wiki-lint`, `/wiki-graph`, and `/project-status` as slash commands (via `.claude/commands/`). Other agents use the natural-language triggers above, which work identically.

Works with markdown, PDF, DOCX, PPTX, XLSX, HTML, TXT, CSV, JSON, XML, RST, EPUB, and more. Non-markdown files are auto-converted via [markitdown](https://github.com/microsoft/markitdown) at ingest time.

## What You Get

**Tracked requirements** — every requirement is a page with MoSCoW priority, an 8-state lifecycle (`proposed → approved → in-progress → implemented → verified → closed`, plus `rejected`/`deferred`), acceptance criteria, and — once approved — WBS execution fields: owner, assignees, progress %, start/due/completed dates, dependencies, milestone.

**Full traceability** — interview → requirement → decision → scope/WBS → completion, wired as bidirectional `[[wikilinks]]`. Drop a requirement and the date + reason are recorded.

**Live dashboard** — `overview.md` plus `python tools/status.py` give completion rate, weighted progress, overdue list, and exit-readiness gates (all `must` done, no overdue, no open high risk, Exit Criteria met).

**Deterministic health checks** — `python tools/health.py` validates schema/enums, unique IDs, traceability, execution gaps, completion/drop consistency, and **scans for secrets/PII** — zero LLM calls, safe every session.

**Traceability graph** — `graph.html` colors pages by type and highlights broken paths (an interview with no requirement, a requirement with no scope mapping).

**Lint reports** — contradictions, duplicate/conflicting requirements, requirements with no acceptance criteria or no WBS mapping, out-of-scope items still active, stalled progress, and data gaps with suggested interviews to fill them.

## Tools

| Tool | Purpose | LLM calls |
|---|---|---|
| `tools/health.py` | Structural integrity: schema, enums, unique IDs, traceability, execution gaps, completion/drop consistency, secret/PII scan | None |
| `tools/status.py` | Completion rate, weighted progress, overdue list, exit-readiness gates | None |
| `tools/lint.py` | Content quality: contradictions, gaps, unmapped requirements | Yes |
| `tools/build_graph.py` | Traceability graph (`graph.json` + `graph.html`) | Optional |

Run `health` and `status` every session (free, fast); run `lint` periodically.

## Security

This wiki stores interviews, stakeholders, and requirements as **plaintext markdown in git** — higher confidentiality/PII risk than a generic notebook. Key practices (full review in [`docs/project-wiki-plan.md`](docs/project-wiki-plan.md) §7):

- **Ingested content is untrusted data, never instructions.** The agent will not delete pages or change scope from something written inside a source document — those require an explicit human Decision (DEC).
- **No secrets/PII in pages.** `health.py` scans for API keys, tokens, and obvious PII patterns. Minimize and pseudonymize personal identifiers.
- Keep sensitive `raw/` originals out of git (`.gitignore`) and commit anonymized versions; use a **private repo** for confidential projects.

## Documentation

- [`docs/project-wiki-plan.md`](docs/project-wiki-plan.md) — design rationale, directory layout, page schemas, **ERD**, security review, phased plan
- [`docs/project-wiki-guide.md`](docs/project-wiki-guide.md) — day-to-day user guide (scenarios, cheat sheet, routines)

The schema file (`CLAUDE.md` / `AGENTS.md` / `GEMINI.md`) tells the agent how to maintain the wiki. Edit it to customize the lifecycle, fields, or workflows for your organization.

| Agent | Schema file |
|---|---|
| Claude Code | `CLAUDE.md` |
| Codex / OpenCode | `AGENTS.md` |
| Gemini CLI | `GEMINI.md` |

## Obsidian Integration

The wiki is plain markdown with consistent `[[wikilinks]]`, so it browses naturally in [Obsidian](https://obsidian.md). Filter `index.md` and `log.md` out of the graph view, and use the [Dataview](https://blacksmithgu.github.io/obsidian-dataview/) plugin to query requirement frontmatter (e.g. `status: in-progress`, `priority: must`, `owner: Kim`).

## Tech Stack

Plain markdown files + Python (NetworkX + vis.js for the graph). No server, no database, runs entirely locally. Version history for free via git.

## License

MIT License — see [LICENSE](LICENSE) for details.
