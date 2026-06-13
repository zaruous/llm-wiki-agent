# Project Demo — 사내 경비 정산 모바일 앱

A worked example of the **project management wiki**: one kickoff interview
ingested, distilled into tracked requirements, then approved / scheduled /
dropped — showing the full traceability chain end to end.

## What's here

- `raw/interviews/2026-06-13-kickoff.md` — the source interview (untrusted input)
- `wiki/` — the pages the agent produces from it:
  - `interviews/INT-001.md` — interview record with extracted requirements
  - `requirements/REQ-001.md` — OCR upload — `must`, **in-progress (40%)**, owner + WBS + schedule
  - `requirements/REQ-002.md` — 2-step approval — `must`, **approved**, `depends_on: [REQ-001]`
  - `requirements/REQ-003.md` — multi-currency — `should`, **deferred** (note `dropped_date` + `dropped_reason`)
  - `decisions/DEC-001.md`, `DEC-002.md` — scope-confirm and defer decisions
  - `stakeholders/ParkJimin.md`, `KimYeonwoo.md`
  - `milestones/M-001.md`, `scope/scope.md`, `charter.md`, `index.md`, `overview.md`, `log.md`

## Traceability chain illustrated

```
INT-001 ──derives──> REQ-001 (OCR)        ──approved by──> DEC-001 ──> M-001
        ──derives──> REQ-002 (approval)   ──depends_on──> REQ-001
        ──derives──> REQ-003 (currency)   ──deferred by──> DEC-002 (dropped 2026-06-13)
```

## Try it

Copy the demo into the live wiki, then run the deterministic tools:

```bash
cp -r examples/project-demo/wiki/* wiki/
python tools/health.py     # schema, traceability, execution gaps, secret scan
python tools/status.py     # completion rate, weighted progress, exit gates
python tools/build_graph.py --open   # traceability graph
```

Expected status: completion **0%** (0 done / 2 in base, 1 deferred excluded),
weighted progress **20%** (REQ-001 40% + REQ-002 0%), **2 `must` open**, no overdue,
exit readiness **not ready**.

Restore the empty wiki afterward with `git checkout -- wiki/ && git clean -fd wiki/`.
