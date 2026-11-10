<div align="center">
  <h3>촌수의사 · mnm-data</h3>
  <p>고령·소규모 한우농가가 말로 남긴 농장 일지를, 신고할 때 접수자(축협·방역기관)에게 한 장 요약으로 함께 전달하는 신고·기록·방역 업무 지원 AI</p>
  <p><b>DB 마이그레이션 · 공공데이터 수집 · 방역지침 지식베이스</b></p>
  <p>
    <img src="https://img.shields.io/badge/PostgreSQL-Migrations-4169E1?logo=postgresql&logoColor=white" alt="PostgreSQL" />
    <img src="https://img.shields.io/badge/Python-ETL-3776AB?logo=python&logoColor=white" alt="Python" />
    <img src="https://img.shields.io/badge/AWS S3-Raw data-232F3E?logo=amazons3&logoColor=white" alt="AWS S3" />
    <img src="https://img.shields.io/badge/Public Data-3 sources-0F766E" alt="Public Data" />
    <img src="https://img.shields.io/badge/RAG-Knowledge Base-7C3AED" alt="RAG" />
  </p>
  <sub>팀 M&amp;M's · 공모전 본선 MVP · 조직 <a href="https://github.com/mnms-chonsu-lab">mnms-chonsu-lab</a></sub>
</div>

---

## 목차

- [이 레포가 맡는 것](#이-레포가-맡는-것)
- [빠른 시작](#빠른-시작)
- [환경변수](#환경변수)
- [기술 스택](#기술-스택)
- [디렉터리 구조](#디렉터리-구조)
- [서비스 구성과 데이터 흐름](#서비스-구성과-데이터-흐름)
- [다른 레포와의 연결 방식](#다른-레포와의-연결-방식)
- [팀 소개](#팀-소개)
- [작업 흐름](#작업-흐름)
- [데이터 출처·라이선스](#데이터-출처라이선스)

---

## 이 레포가 맡는 것

| 구분 | 담당 부분 |
| --- | --- |
| DB 스키마 | `migrations/` — **DB 구조 변경은 여기서만** 합니다 |
| 공공데이터 수집 | 가축 질병 발생 정보, 사육규모별 농장 통계, 거점소독시설 ETL + 법정동 `region_code` 통일 |
| 방역지침 지식베이스 | 구제역·럼피스킨 SOP, 가축전염병 예방법 원문, 조항 분할, 검수 기록 (`mnm-ai/agents/guide_rag`가 참조) |
| 시드 데이터 | 개발용 시드 (`seed/`) |
| 문서 | ERD (`docs/erd/`) |

> 현재 상태: 디렉터리 골격과 README만 있고 마이그레이션·ETL·지식베이스 본문은 아직 없습니다. 아래 🚧 표시는 모두 구현 예정입니다.

---

## 빠른 시작

```bash
git clone https://github.com/mnms-chonsu-lab/mnm-data.git
cd mnm-data
cp .env.example .env      # DATABASE_URL, PUBLIC_DATA_API_KEY 등 채우기
```

| 단계 | 명령 | 상태 |
| --- | --- | --- |
| 마이그레이션 적용 | `migrations/README.md`의 도구·명령 | 🚧 구현 예정 (도구 미정) |
| ETL 실행 | `etl/outbreak`, `etl/farm_scale`, `etl/disinfection_facility` | 🚧 구현 예정 |
| 지식베이스 검수 | `knowledge-base/` 조항 분할·검수 기록 | 🚧 구현 예정 |
| 시드 적재 | `seed/README.md` | 🚧 구현 예정 |

> 모델 가중치·원본 데이터는 git에 넣지 않습니다. S3 / MLflow에서 가져와 사용합니다.

---

## 환경변수

값은 `.env.example`을 복사해 `.env`에 채웁니다. 실제 키는 커밋하지 않습니다.

| 변수 | 위치 | 용도 | 없으면 |
| --- | --- | --- | --- |
| `DATABASE_URL` | `migrations/`, `etl/*`, `seed/` | PostgreSQL 접속 문자열 | 마이그레이션·적재 불가 |
| `PUBLIC_DATA_API_KEY` | `etl/*` | 공공데이터 API 호출 | 공공데이터 수집 불가 |
| `AWS_ACCESS_KEY_ID` | `etl/*` | S3 원본 데이터 접근 | 원본 업로드·다운로드 불가 |
| `AWS_SECRET_ACCESS_KEY` | `etl/*` | S3 접근 | 위와 같음 |
| `AWS_REGION` | `etl/*` | AWS 리전 | 위와 같음 |
| `S3_BUCKET_NAME` | `etl/*` | 원본 데이터 버킷 | 위와 같음 |

---

## 기술 스택

| 영역 | 기술 | 용도 |
| --- | --- | --- |
| DB | PostgreSQL | 서비스 데이터 저장소 (스키마의 단일 출처) |
| 마이그레이션 | 🚧 도구 미정 | 스키마 버전 관리 |
| ETL | Python | 공공데이터 3종 수집·정제, `region_code` 통일 |
| 저장소 | AWS S3 | 공공데이터 원본 |
| 지식베이스 | 마크다운·조항 단위 분할 | SOP·법령 원문 (RAG 입력) |

---

## 디렉터리 구조

```
mnm-data/
├── migrations/                 # DB 스키마 마이그레이션 — 구조 변경은 여기서만
├── etl/
│   ├── outbreak/               # 가축 질병 발생 정보
│   ├── farm_scale/             # 사육규모별 농장 통계
│   └── disinfection_facility/  # 거점소독시설 (+ 법정동 region_code 통일)
├── knowledge-base/
│   ├── sop/                    # 구제역·럼피스킨 SOP 원문
│   ├── law/                    # 가축전염병 예방법 등 법령 원문
│   └── review-log/             # 조항 분할·검수 기록
├── seed/                       # 개발용 시드 데이터
├── docs/
│   └── erd/                    # ERD
├── .github/                    # 이슈·PR 템플릿, CODEOWNERS, 라벨
├── .env.example
├── CONTRIBUTING.md · CLAUDE.md · AGENTS.md
└── README.md
```

---

## 서비스 구성과 데이터 흐름

이 레포는 흐름의 **바탕이 되는 데이터**를 맡습니다. 서비스 DB 스키마, 공공데이터, 안내 문구의 근거가 되는 공식 원문을 관리합니다.

```
농가 음성·사진
  → STT · LLM 구조화
  → 일지 · 신고서 초안
  → 부위 일치 검증
  → 농가 승인
  → 요약 카드
  → 선택한 신고 경로로 전달 (전화 · 사이트 · 축협)
  → 접수자 웹 열람
```

**지키는 원칙**

| 원칙 | 내용 |
| --- | --- |
| 판정하지 않음 | 질병·신고 여부를 판정하지 않는다. 확률·자동 신고로 읽히는 표현을 쓰지 않는다 |
| `[바로 신고]` 상시 노출 | 모든 화면에 항상 보인다 |
| 공식 문구만 | 안내 문구는 공식 지침(SOP·법령) 원문만 사용한다 |
| 승인된 기록만 전달 | 농가가 승인한 기록만 접수자에게 넘어간다 |

---

## 다른 레포와의 연결 방식

| 방향 | 규칙 |
| --- | --- |
| mnm-data → mnm-dev | DB 구조 변경은 `migrations/`에서만 합니다. mnm-dev 백엔드(`services/api`)는 그 마이그레이션을 적용해서 쓰고 직접 스키마를 바꾸지 않습니다 |
| `migrations/` 변경 | @dooooing 승인, PR 리뷰어로 지정합니다 |
| mnm-data → mnm-ai | `knowledge-base/`의 SOP·법령 원문은 `mnm-ai/agents/guide_rag` 등이 참조만 합니다. 원문 추가·수정은 이 레포에서만 합니다 |
| PR 링크 | 다른 레포에 영향을 주는 PR은 본문에 관련 레포 PR·이슈 링크를 반드시 넣습니다 |

- [mnm-dev](https://github.com/mnms-chonsu-lab/mnm-dev) — 농가 앱·접수자 웹·백엔드·배포
- [mnm-ai](https://github.com/mnms-chonsu-lab/mnm-ai) — 에이전트·규칙·인식 모델

---

## 팀 소개

| 이름 | 역할 | GitHub |
| --- | --- | --- |
| 이유민 | PM · Frontend | [@kkamret](https://github.com/kkamret) |
| 이인서 | Backend · Infra · MLOps | [@dooooing](https://github.com/dooooing) |
| 박명훈 | AI | [@parkmyeonghun](https://github.com/parkmyeonghun) |
| 서인교 | Data | [@tjdlsry](https://github.com/tjdlsry) |

**일정**: 11/21 기능 개발 마감(이후 버그 수정만) → 11/22 운영 배포 → 11/22~27 QA·안정화 → 11/28 제출

---

## 작업 흐름

```
이슈 (템플릿 선택) → 브랜치 → develop으로 PR → 리뷰 → squash merge
```

| 항목 | 규칙 |
| --- | --- |
| 이슈 | `.github/ISSUE_TEMPLATE/`의 템플릿 5개 중 선택 (빈 이슈 금지) |
| 브랜치 | `YYYYMMDD_#이슈번호_요약` — develop에서 분기, 예) `20261112_#12_농가_라우터_STT` |
| PR | `.github/pull_request_template.md` 사용, 대상은 `develop` |
| PR 제목 | `type(영역): 요약 (#이슈번호)` — type: `feat` `fix` `docs` `chore` `test` `refactor` |
| 머지 | squash merge만, 머지 후 브랜치 자동 삭제 |
| 원칙 | 1 이슈 = 1 브랜치 = 1 PR |

자세한 규칙: [CONTRIBUTING.md](./CONTRIBUTING.md) · AI 도구 사용 시: [CLAUDE.md](./CLAUDE.md), [AGENTS.md](./AGENTS.md)


---

## 데이터 출처·라이선스

| 데이터 | 출처 | 이 서비스에서의 용도 | 이용 조건 |
| --- | --- | --- | --- |
| 가축 질병 발생 정보 | 민관협력 지원 플랫폼 공공데이터 | 발생 현황 참고 | 제공처 이용 조건 확인 필요 |
| 사육규모별 농장 통계 | 민관협력 지원 플랫폼 공공데이터 | 농가 규모 정보 | 제공처 이용 조건 확인 필요 |
| 거점소독시설 | 민관협력 지원 플랫폼 공공데이터 | 소독 시설 안내 | 제공처 이용 조건 확인 필요 |
| 구제역·럼피스킨 SOP, 가축전염병 예방법 | 공식 지침·법령 | 안내 문구 원문 | 공문서·법령 원문 (출처 표기) |
| 한우 행동 데이터 | AI-Hub | 소 행동 인식 모델(YOLO11s) 학습·평가 | **AI-Hub 이용약관 준수** — 원본 재배포 금지, git 커밋 금지 |
| 부위 판정 이미지 | FMD Cattle, Cattle side/back view | 부위 일치 검증 모델(SigLIP 2) 학습·평가 | FMD Cattle: **CC BY 4.0** (출처 표기). Cattle side/back view: 🚧 라이선스 확인 중 |

> 🚧 레포 자체 라이선스는 아직 정하지 않았습니다. 정해지면 이 절에 추가합니다.
> 원본 데이터·모델 가중치는 git에 넣지 않고 S3 / MLflow에서 관리합니다.
