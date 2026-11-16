# [확인 요청] 지식베이스 1차 적재(11/16) · 방역 안내 원문 일치 확인

- 명세서: https://claude.ai/artifact/5S3Eeyw2TqzhbP7Lx9S3ad
- 작성일: 2026-11-16

@tjdlsry @parkmyeonghun 확인 부탁드려요!

- [ ] (인교님) 지식베이스 1차 적재 11/16 (REQ-DATA-05)
  - `biosecurity_rule.stage` 값: `suspect` | `after_report` | `regional`
  - 원문 근거 필수: 문서명·조항·개정일, 게시(`published`) 상태만 검색 대상
  - 적재 완료되면 이 PR에 코멘트로 알려주세요
- [ ] (명훈님) 적재 후 `/ai/guide` 결과가 조항 원문과 같은지 확인 (LLM은 조항 고르기만, 새 문장 생성 금지)
  - 근거 없으면 `RAG-NONE` + `detail.fallback = true`
- 참고: 일지 분류 9개 확정 — 사육현황 · 접종 · 소독 · 관찰 · 출입 · 출생 · 폐사 · 이동 · 메모 (DB에는 서버 자동 기록용 "신고" 1개 추가)
