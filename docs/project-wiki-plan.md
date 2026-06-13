# 프로젝트 관리 위키 재구성 — 구현계획

> 브랜치: `project.lifecycle-wiki`
> 작성일: 2026-06-13
> 상태: 제안 (Draft)

## 1. 배경 & 콘셉트 전환

현재 `llm-wiki-agent`는 **범용 지식베이스** 콘셉트다. 소스 문서를 `ingest`하면
요약 페이지(`sources/`) + 엔티티(`entities/`) + 개념(`concepts/`)을 자동 생성하고
`[[wikilinks]]`로 교차연결한다.

이 엔진(인입 → 정제 → 교차연결 → 그래프 → 린트)을 그대로 살리되,
**대상을 "프로젝트 라이프사이클"로 재정의**한다.

| 구분 | 기존 (지식 위키) | 신규 (프로젝트 관리 위키) |
|---|---|---|
| 인입 대상 | 논문/기사/책 | 인터뷰 녹취, 요구사항 문서, 회의록, 메일 |
| 산출 페이지 | source / entity / concept | requirement / interview / decision / scope / stakeholder / risk |
| 핵심 가치 | 지식 누적 & 교차참조 | **요구사항 추적성(traceability) & 종료범위 관리** |
| overview | 주제 종합 | **프로젝트 현황 대시보드** (진행률/범위/리스크) |

### 핵심 가치: 추적성(Traceability) 체인

```
인터뷰(발화)  →  요구사항(정제)  →  범위/WBS(계획)  →  구현 상태  →  완료기준(DoD) 충족
   INT-001          REQ-012          SCOPE / WBS        status         verified/closed
```

한 요구사항이 "어느 인터뷰에서 나왔고, 어떤 의사결정을 거쳐, 범위 안인지, 지금
어떤 상태이며, 완료 기준을 충족했는지"를 한 줄로 추적한다. 인터뷰부터 프로젝트
종료범위 확정까지 전 구간을 위키 하나로 관리하는 것이 목표.

---

## 2. 디렉토리 구조 (재구성안)

```
raw/                  # 원본 (인터뷰 녹취/요구사항서/회의록/메일) — 불변
wiki/
  index.md            # 전체 카탈로그 — 인입 시마다 갱신
  log.md              # 작업 로그 (append-only)
  overview.md         # ★ 프로젝트 현황 대시보드 (진행률·범위·오픈리스크)
  charter.md          # ★ 프로젝트 헌장: 목표/비전/성공기준/범위(In·Out)/이해관계자
  requirements/       # 요구사항 페이지 (REQ-XXX)
  interviews/         # 인터뷰·회의 기록 (INT-XXX)
  scope/              # 범위 정의 / WBS / 완료기준(DoD) / 종료기준(Exit Criteria)
  decisions/          # 의사결정 기록 (DEC-XXX, ADR 스타일)
  stakeholders/       # 이해관계자 (사람·조직·역할)
  milestones/         # 마일스톤 / 일정 / 게이트
  risks/              # 리스크 (RISK-XXX)
  syntheses/          # 질의 답변·분석 리포트
graph/                # 추적성 그래프 (graph.json + graph.html)
tools/                # health.py / lint.py / build_graph.py (PM용으로 확장)
docs/                 # 본 계획 등 메타 문서
```

> **코어위키 통합 지점**: 사용자가 별도로 만든 "코어위키"는 Phase 4에서 병합한다.
> 도메인 공통 페이지(용어집·표준·정책 등)는 `wiki/core/` 하위로 흡수하거나
> 기존 디렉토리에 매핑한다. 통합 시 ID/네이밍 충돌만 점검하면 된다.

---

## 3. 페이지 포맷 (목차/스키마)

### 3.1 공통 frontmatter

```yaml
---
id: REQ-001            # 타입별 접두어 + 일련번호 (요구사항/인터뷰/의사결정/리스크)
title: ""
type: charter | requirement | interview | stakeholder | decision | milestone | risk | scope | synthesis
tags: []
last_updated: YYYY-MM-DD
---
```

### 3.2 요구사항 페이지 (`requirements/REQ-XXX.md`) — 핵심

```yaml
---
id: REQ-001
title: "요구사항 한 줄 제목"
type: requirement
category: functional | non-functional | constraint
priority: must | should | could | wont        # MoSCoW
status: proposed | approved | in-progress | implemented | verified | closed | rejected | deferred
source_interviews: [INT-001]                   # 출처 추적
# --- 실행/WBS 관리 (요구사항 확정 후 채움) ---
wbs_id: "1.2.3"                                # WBS 번호 (계층)
owner: "담당자"                                 # 책임자
assignees: ["작업자A", "작업자B"]              # 실제 수행자
progress: 0                                    # 진척률 0–100 (%)
start_date: YYYY-MM-DD                          # 착수 예정/실제
due_date: YYYY-MM-DD                            # 종료 목표
completed_date: YYYY-MM-DD                      # 실제 완료일 (verified/closed 시)
estimate: "5d"                                  # 예상 공수 (선택)
actual: "6d"                                    # 실제 공수 (선택)
depends_on: [REQ-002]                           # 선행 요구사항/작업
milestone: [[M1]]                               # 귀속 마일스톤
tags: []
last_updated: YYYY-MM-DD
---

## 설명
무엇을, 왜 필요한가.

## 배경 / 근거
> "원문 발언 인용" — [[INT-001]] (출처 인터뷰)

## 인수 조건 (Acceptance Criteria / DoD)
- [ ] 조건 1
- [ ] 조건 2

## 작업 분해 (WBS Tasks) — 확정 후
| # | 작업 | 담당 | 시작 | 종료 | 상태 | 진척 |
|---|---|---|---|---|---|---|
| 1.2.3.1 | ... | 작업자A | 06-15 | 06-18 | in-progress | 40% |
| 1.2.3.2 | ... | 작업자B | 06-18 | 06-20 | todo | 0% |

## 연결 (Connections)
- [[INT-001]] — 도출된 인터뷰
- [[DEC-003]] — 관련 의사결정
- [[M1]] — 귀속 마일스톤
- [[SCOPE]] — WBS 매핑 항목

## 상태 이력 (Status / Schedule Log)
- 2026-06-13 proposed → approved (DEC-003)
- 2026-06-15 start (assignee: 작업자A), progress 0%
- 2026-06-18 progress 40%

## 변경 / 모순
- [[REQ-009]]와 우선순위 충돌
```

> **수명주기**: 요구사항은 `proposed→approved` 단계까지는 추적성(출처/근거) 중심으로
> 관리되고, **`approved` 확정 시점부터 WBS 필드(wbs_id·assignees·progress·
> start/due/completed·depends_on)를 채워** 실행/진척을 관리한다. 미확정 요구사항은
> 해당 필드를 비워두며, `health.py`는 `approved+` 상태인데 담당자/일정이 비면 경고한다.

### 3.3 인터뷰 페이지 (`interviews/INT-XXX.md`)

```yaml
---
id: INT-001
title: "이해관계자 인터뷰 — 제목"
type: interview
interview_type: discovery | requirements | review | retrospective
date: YYYY-MM-DD
participants: [[[StakeholderName]]]
tags: []
last_updated: YYYY-MM-DD
---

## 목적
## 핵심 논의
## 도출 요구사항 (Extracted Requirements)
- [[REQ-001]] — 발언 근거 요약
## 의사결정
- [[DEC-001]]
## 액션 아이템
- [ ] 담당 / 기한
## 미해결 · 후속 질문
```

### 3.4 범위 페이지 (`scope/`) — 종료범위 관리 핵심

```yaml
---
title: "프로젝트 범위 / WBS"
type: scope
last_updated: YYYY-MM-DD
---

## WBS (작업 분해 구조 + 일정)
| WBS | 항목 | 요구사항 | 담당 | 시작 | 종료 | 상태 | 진척 |
|---|---|---|---|---|---|---|---|
| 1 | (대분류) | — | — | — | — | — | — |
| 1.2 | (중분류) | [[REQ-001]] | 작업자A | 06-15 | 06-20 | in-progress | 40% |
| 1.3 | (중분류) | [[REQ-002]] | 작업자B | 06-21 | 06-28 | todo | 0% |
## In-Scope (포함)
- WBS 1.2 ... → [[REQ-001]], [[REQ-002]]
## Out-of-Scope (제외)
- ... (제외 사유 / 관련 [[DEC-XXX]])
## 완료 정의 (Definition of Done)
- 모든 must 요구사항이 verified 상태 (progress 100%)
## 프로젝트 종료 기준 (Exit Criteria)
- ...
## 범위 변경 이력 (Scope Change Log)
- 2026-06-13 REQ-015 추가 (DEC-007)
```

> WBS는 `scope/`에서 **프로젝트 전체 일정·진척을 한눈에** 보는 마스터 테이블이고,
> 각 요구사항 페이지의 "작업 분해(WBS Tasks)"는 그 요구사항 **내부 세부 작업**이다.
> 두 곳의 진척/일정은 요구사항 frontmatter(`progress`·`start_date`·`due_date`)를
> 단일 출처(source of truth)로 삼아 동기화한다.

### 3.5 기타 페이지

- **의사결정** `decisions/DEC-XXX.md` (ADR): 맥락 / 결정 / 대안 / 결과 / 영향받는 요구사항
- **이해관계자** `stakeholders/Name.md`: 역할 / 관심사 / 영향력 / 관련 인터뷰·요구사항
- **마일스톤** `milestones/`: 목표일 / 게이트 기준 / 포함 요구사항
- **리스크** `risks/RISK-XXX.md`: 발생가능성·영향도 / 대응전략 / 트리거 / 관련 요구사항

---

## 4. 워크플로우 재정의

| 커맨드 | 기존 동작 | 신규 동작 |
|---|---|---|
| `/wiki-ingest` | 소스→요약/엔티티/개념 | **인터뷰·문서 인입** → 인터뷰 페이지 + 요구사항 후보 추출 + 의사결정/이해관계자 갱신 + 추적성 링크 연결 |
| `/wiki-query` | 주제 질의 | **프로젝트 질의** ("미해결 must 요구사항?", "범위 변경 이력?") — 상태/우선순위 필터 |
| `/wiki-health` | 구조 점검 | + 요구사항 ID 유니크·상태 enum 검증, 인터뷰↔요구사항 추적성 누락 탐지 |
| `/wiki-lint` | 품질 점검 | + 인수조건/구현 매핑 누락, 모순 요구사항, 범위 밖 요구사항, 우선순위 충돌 |
| `/wiki-graph` | 위키링크 그래프 | **추적성 그래프** — 인터뷰→요구사항→범위 연결망, 끊어진 추적경로 강조 |
| `/project-status` (신규) | — | **진행률 대시보드**: 상태별 요구사항 집계, 범위 완료율, 오픈 리스크 |

### 인입(ingest) 단계 재정의
1. 원본 인터뷰/문서를 Read (비마크다운은 markitdown 자동변환)
2. `index.md` / `overview.md` / `charter.md` 로 현재 맥락 파악
3. `interviews/INT-XXX.md` 작성
4. **요구사항 후보 추출** → 신규 `requirements/REQ-XXX.md` 작성 또는 기존 갱신
5. 의사결정·이해관계자·리스크 페이지 갱신
6. 추적성 링크(`source_interviews`, `[[wikilinks]]`) 양방향 연결
7. 모순/우선순위 충돌 플래그
8. `index.md` 갱신, `overview.md` 대시보드 수치 갱신
9. `log.md` append: `## [YYYY-MM-DD] ingest | <Title>`
10. 사후 검증: 끊어진 링크/고아 요구사항 점검

### 종료범위(완료) 집계 규칙
```
완료율(건수)   = (verified + closed 요구사항 수) / (전체 - rejected - deferred)
진척률(가중)   = Σ(요구사항 progress) / (대상 요구사항 수)   # 부분 진행 반영
지연 요구사항  = status ∉ {verified,closed} AND due_date < today

프로젝트 종료 가능 = 모든 must 요구사항 status ∈ {verified, closed} (progress 100%)
                    AND 오픈 리스크 中 high 없음
                    AND 지연 요구사항 없음
                    AND scope/Exit Criteria 전 항목 충족
```

---

## 5. tools/ 확장 계획

| 도구 | 추가 검사 |
|---|---|
| `health.py` | 요구사항 ID 유니크/포맷, `status`·`priority` enum 유효성, 인터뷰↔요구사항 양방향 링크 존재, **approved+ 인데 담당자/일정 누락**, `progress` 범위(0–100)·완료상태 정합성(verified면 100%) |
| `lint.py` | 인수조건 없는 요구사항, 구현/범위 미매핑, 모순·중복 요구사항, Out-of-scope인데 활성 상태, **due_date 초과(지연)·진척 정체** |
| `build_graph.py` | 노드 타입별 색상(요구사항/인터뷰/이해관계자/리스크), 추적성 경로 끊김 분석, **선행관계(depends_on) 엣지** |
| `status.py` (신규, 선택) | 상태별 집계·완료율·**진척률 가중 집계·일정 지연 목록·번다운/간트 리포트** (LLM 불필요, 결정론적) |

---

## 6. 단계별 구현계획 (Phases)

| Phase | 내용 | 산출물 |
|---|---|---|
| **0** | 브랜치 생성 + 본 계획 문서 | `project.lifecycle-wiki`, `docs/project-wiki-plan.md` ✅ |
| **1** | 스키마 재작성 | `CLAUDE.md` / `AGENTS.md` / `GEMINI.md` 를 PM 콘셉트로 갱신 |
| **2** | 디렉토리 스캐폴딩 + 시드 | `wiki/` 새 구조, 템플릿, `charter.md`/`overview.md` 시드, 슬래시 커맨드 갱신 + `/project-status` 추가 |
| **3** | 도구 확장 | `health.py`/`lint.py`/`build_graph.py` PM 검사 추가, (선택) `status.py` |
| **4** | **코어위키 병합** | 사용자 제공 코어위키 흡수(`wiki/core/` 또는 매핑), 샘플 인터뷰 1건 ingest로 E2E 검증 |
| **5** | 문서화 | `README.md` 갱신, 사용 예시(인터뷰→요구사항→완료) |

> Phase 0 완료 후 Phase 1~3을 진행하고, **코어위키가 준비되면 Phase 4**에서 병합한다.

---

## 7. 다음 액션

1. 본 계획 리뷰 & 확정
2. 코어위키 자료 공유 (병합 대상/형식 확인)
3. 확정 시 Phase 1(스키마 재작성)부터 순차 진행
```