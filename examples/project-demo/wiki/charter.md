---
title: "Project Charter — 사내 경비 정산 모바일 앱"
type: charter
tags: []
last_updated: 2026-06-13
---

# Project Charter

## Goal / Vision
종이 영수증 + 엑셀 기반 경비 정산을 모바일 앱으로 전환해 재무팀 부하를 줄이고
직원 정산 경험과 감사 추적성을 개선한다.

## Success Criteria
- 월말 정산 처리 시간 50% 단축
- 영수증 수기 입력 제거(OCR 자동 인식 ≥ 90%)

## Scope Summary
- **In:** 영수증 OCR 업로드([[REQ-001]]), 2단계 결재([[REQ-002]]) — see [Scope / WBS](scope/scope.md)
- **Out:** 해외 다중 통화([[REQ-003]], [[DEC-002]])

## Stakeholders
- [[ParkJimin]] — 재무팀 리드 (업무 오너)
- [[KimYeonwoo]] — 개발 PM (실행 오너)

## Milestones
- [[M-001]] — 1차 릴리스 (MVP), 2026-07-15

## Constraints & Assumptions
- 예산 빠듯 → 1차 범위 최소화
- 감사 대응 위해 결재 이력 영구 보존 필요

## Data Retention Policy
- 영수증 이미지/개인정보는 사내 정책에 따라 보존, 인터뷰 원본에는 식별자 최소화.
