# migrations

DB 스키마 마이그레이션. **DB 구조 변경은 이 디렉터리에서만** 합니다. mnm-dev(`services/api`)는 여기 마이그레이션을 적용해서 사용합니다.

- **담당**: @tjdlsry (+ @dooooing 공동 승인)

## 파일

| 파일 | 내용 |
| --- | --- |
| `0001_init_operational.sql` | 운영 데이터·공공데이터 테이블 26개 (MVP 기능명세서 v1.0 11/16 데이터 모델 기준, 이름 대응은 `rename_decisions.md`) |
| `0002_init_ml.sql` | AI 학습 데이터 테이블 3개 (`aihub_behavior_label`, `part_image_dataset`, `dataset_version`) |
| `0003_biosecurity_rule_embedding.sql` | `biosecurity_rule.embedding` 컬럼 (`pgvector` 필요) |
| `0004_inference_log_http_status.sql` | `inference_log.http_status` 컬럼 (AI 오류율: 503·504만 실패, mnm-ai#14) |

## 적용 방법

- 도구: 순수 SQL 파일 (마이그레이션 도구 미정)
- 순서: `0001` → `0002` → `0003` → `0004` (번호 순)
- 각 파일은 `BEGIN` … `COMMIT`으로 감싸져 있음 → 중간에 오류가 나면 그 파일 전체가 취소됨
- 대상: PostgreSQL 17 (staging에서 확인), `0003`은 `pgvector` 확장 필요

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f migrations/0001_init_operational.sql
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f migrations/0002_init_ml.sql
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f migrations/0003_biosecurity_rule_embedding.sql
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f migrations/0004_inference_log_http_status.sql
```

- DBeaver를 쓸 때는 파일을 열고 연결을 고른 뒤 스크립트 전체 실행(Alt+X)

## 변경 규칙

- develop에 머지된 파일은 고치지 않음 → 바꿀 것이 있으면 다음 번호 파일(`0004_...sql`)을 추가
- 변경 PR은 리뷰어 @dooooing 지정
