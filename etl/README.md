# etl

공공데이터 3종 수집. 명세 DATA-02 · A-06(ADM-09) · REQ-OPS-06(수집 작업 실패 알람).

| 작업 (`etl_job_run.job`) | 실행 | 주기 (명세) | 출처 | 적재 방식 |
| --- | --- | --- | --- | --- |
| `outbreak` | `python etl/outbreak/collect.py` | 일 1회 | 농림축산식품 공공데이터포털 「가축질병발생정보」 `Grid_20151204000000000316_1` | 축종 `소-`로 시작하는 행(소 전체), 발생 번호 기준 덮어쓰기 |
| `disinfection_facility` | `python etl/disinfection_facility/collect.py` | 일 1회 | 같은 포털 「거점소독시설안내」 `Grid_20220621000000000618_1` | 전체 지우고 다시 넣기 |
| `farm_scale` | `python etl/farm_scale/collect.py` | 월 1회 | 공공데이터포털 15147310 (원본 갱신 연 1회) | `build_farm_scale_sql.py` 가 만든 SQL 실행 |
| (어드민 [지금 수집]) | `python etl/run_requested.py` | 5분마다 | `etl_job_run`의 `requested` 행 | 요청된 작업의 수집 스크립트 실행 |

## 동작
- 실행마다 `etl_job_run`에 `running` → `success`(건수) / `failed`(원인) 기록. 어드민 대시보드가 이 표를 읽음.
- 어드민 [지금 수집](ADM-09): 백엔드가 `status = 'requested'` 행을 넣으면 `run_requested.py`가 실행. 수집 스크립트는 그 행을 이어받아 `running` → `success`/`failed`로 바꿈 (요청이 없으면 새 행). 같은 작업이 `running`이면 다음 확인 때 실행.
- 적재는 한 트랜잭션. 실패하면 전체 취소 → 직전 데이터 유지.
- API가 0건이거나 받은 건수가 `totalCnt`와 다르면 실패로 봄 (일부만 받은 데이터로 덮어쓰지 않음).
- 실패하면 `ALERT_WEBHOOK_URL`(mnm-dev #38 감시 프로그램과 같은 웹훅)로 알림, 종료 코드 1. 비어 있으면 화면 출력만.
- 오류 문구·알림에 인증키를 넣지 않음. 농장명(`FARM_NM`)은 DB·원본 저장 모두 넣지 않음.
- 원본 응답(JSON)은 Object Storage `raw/{데이터}/YYYYMMDD/`에 저장. 설정이 없거나 실패해도 적재는 계속.
- 법정동 코드 공식 변경표 `etl/official_map.csv`는 git 제외(`*.csv`). 없으면 그 단계만 건너뜀.

## 환경변수
| 변수 | 용도 | 없으면 |
| --- | --- | --- |
| `DATABASE_URL` (또는 `DB_HOST`·`DB_PORT`·`DB_NAME`·`DB_USER`·`DB_PASSWORD`) | DB 접속 | 실행 불가 |
| `MAFRA_API_KEY` | 농림축산식품 공공데이터포털 인증키 (`outbreak`, `disinfection_facility`) | 해당 작업 실패 |
| `PUBLIC_DATA_API_KEY` | 공공데이터포털 인증키 (`farm_scale`) | 해당 작업 실패 |
| `ALERT_WEBHOOK_URL`, `ALERT_WEBHOOK_FORMAT`, `MONITOR_ENV_NAME` | 실패 알림 (`discord` 기본 / `slack`, 앞머리 기본 `staging`). mnm-dev `monitor.py`와 같은 값 | 화면 출력만 |
| `S3_ENDPOINT_URL`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `S3_BUCKET_NAME` | 원본 저장 | 원본 저장만 건너뜀 |

## 필요한 패키지
`psycopg[binary]`, `python-dotenv`, `boto3`(원본 저장), `pandas`·`requests`(`farm_scale`)
