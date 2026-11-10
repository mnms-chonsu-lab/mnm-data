# mnm-data

촌수의사 — 한우농가 신고·기록·방역 업무 지원 AI. DB 마이그레이션, 공공데이터 수집, SOP·법령 지식베이스, 시드 데이터를 담당하는 레포입니다. (M&M's, 공모전 본선 MVP)

## 담당
- 전체 — 서인교 (Data)
- `migrations/** `— 이인서(Infra) 공동

## 구성
| 경로 | 내용 |
|---|---|
| `migrations/` | DB 스키마 마이그레이션 — **DB 구조 변경은 여기서만** 합니다 |
| `etl/outbreak/` | 가축전염병 발생 정보 ETL |
| `etl/farm_scale/` | 농가 규모 정보 ETL |
| `etl/disinfection_facility/` | 소독 시설 정보 ETL (+ 법정동 `region_code` 통일) |
| `knowledge-base/` | SOP·법령 원문, 조항 분할, 검수 기록 |
| `seed/` | 개발용 시드 데이터 |
| `docs/erd/` | ERD 문서 |

## 로컬 실행 방법
1. `.env.example`을 복사해 `.env` 생성 후 키 값 채우기 (`DATABASE_URL`, 공공데이터 API 키 등)
2. 마이그레이션 적용: `migrations/README.md`의 도구·명령 참고
3. ETL 실행: 각 `etl/*` 디렉터리 README 참고
4. 시드 데이터 적재: `seed/README.md` 참고

> 원본 데이터(공공데이터 원본, 대용량 파일)는 git에 넣지 않습니다. S3를 사용합니다.

## 브랜치·PR 규칙
- 브랜치: `YYYYMMDD_#이슈번호_요약` (develop에서 분기, 한글 가능, 공백은 `_`)
- 1 이슈 = 1 브랜치 = 1 PR, **develop**으로 PR
- PR 제목: `type(영역): 요약 (#이슈번호)`
- squash merge만 허용, 머지 후 브랜치 자동 삭제
- 자세한 규칙은 [CONTRIBUTING.md](./CONTRIBUTING.md) 참고

## 연결 방식
- **mnm-data → mnm-dev**: DB 구조 변경은 `migrations/`에서만 합니다. mnm-dev(`services/api`)는 이 마이그레이션을 적용해서 사용하며, 직접 스키마를 바꾸지 않습니다. `migrations/` 변경 PR은 @dooooing을 리뷰어로 지정합니다.
- **mnm-data → mnm-ai**: `knowledge-base/`의 SOP·법령 원문은 `agents/guide_rag`(mnm-ai) 등에서 참조만 합니다. 원문 추가·수정은 이 레포에서만 합니다.
- 다른 레포에 영향 주는 PR은 본문에 관련 레포 PR·이슈 링크를 반드시 포함합니다.
