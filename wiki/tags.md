---
title: "Tag Registry"
type: meta
last_updated: ""
---

# Tag Registry (controlled vocabulary)

The formatter (`python tools/format.py`) validates every page's `tags:` against
this registry. A tag is **valid** if it is listed under *Allowed Tags* **or**
begins with one of the *Namespaces* below. Unknown tags are reported (never
auto-deleted) so the vocabulary grows deliberately instead of sprawling.

**Tag style:** lowercase, hyphenated (`kebab-case`), no spaces. The formatter
normalizes case/spacing/duplicates/order automatically; it only *reports*
unknown tags.

## Namespaces (free tags allowed under these prefixes)
- `area/` — business/functional area (e.g. `area/finance`, `area/mobile`)
- `phase/` — lifecycle phase (e.g. `phase/discovery`, `phase/mvp`)
- `component/` — system component (e.g. `component/ocr`, `component/approval`)
- `team/` — owning team (e.g. `team/frontend`)

## Allowed Tags
- kickoff
- mvp
- release
- scope
- ocr
- upload
- approval
- audit
- multi-currency
- deferred
- expense-app
- stub
- finance
- engineering
- security
- compliance
