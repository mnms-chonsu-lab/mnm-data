"""가축위생방역지원본부_전국 시군별 한우 사육규모 현황 (data.go.kr 15147310)
→ farm_scale_statistics 적재용 SQL 파일 생성. 생성된 SQL은 DBeaver에서 실행.

사용법:
    python etl/farm_scale/build_farm_scale_sql.py --api [출력 SQL 경로]      # OpenAPI (기본)
    python etl/farm_scale/build_farm_scale_sql.py "CSV 경로" [출력 SQL 경로]  # 파일 (예비)
    옵션 --years 2025,2026 : 넣을 연도 (기본: FROM_YEAR 이후 전체 연도)

- API: Base URL api.odcloud.kr/api, 경로는 Swagger(infuser.odcloud.kr)에서 실행 시 찾음
- 인증키: .env 의 PUBLIC_DATA_API_KEY (없으면 DATA_GO_KR_KEY)
- 원본 CSV는 git에 올리지 않음 (Object Storage)
- 구간 호수 합 ≠ 전체호수인 행이 있으면 SQL을 만들지 않고 중단
- SQL 동작: 같은 품종의 기존 행 전부 삭제 → 전체 연도 다시 적재 → region_code 채움 → 결과 확인
- reference_ym: 원본에 날짜 없음 → '{년도}.01' (포털 시간범위 "~2026년 1월" 기준)
"""
import json
import os
import sys
from urllib.parse import unquote

import pandas as pd
import requests
from dotenv import load_dotenv

SWAGGER = "https://infuser.odcloud.kr/oas/docs?namespace=15147310/v1"
BASE = "https://api.odcloud.kr/api"

COLS = [  # (원본 컬럼, DB 컬럼)
    ("순번", "seq_no"), ("품종", "breed"), ("시도", "province"), ("시군", "city_county"),
    ("년도", "year"), ("전체호수", "total_farms"), ("전체두수", "total_heads"),
    ("100두 이상(호수)", "farms_over_100"), ("100두 이상(두수)", "heads_over_100"),
    ("100두-50두 이상(호수)", "farms_50to100"), ("100두-50두 이상(두수)", "heads_50to100"),
    ("50두-30두 이상(호수)", "farms_30to50"), ("50두-30두 이상(두수)", "heads_30to50"),
    ("30두-7두 이상(호수)", "farms_7to30"), ("30두-7두 이상(두수)", "heads_7to30"),
    ("7두-0두 이상(호수)", "farms_under7"), ("7두-0두 이상(두수)", "heads_under7"),
]
COLS = [(c.replace(" ", ""), d) for c, d in COLS]   # 원본 컬럼명은 공백 없이 비교
FARM_BANDS = ["farms_over_100", "farms_50to100", "farms_30to50", "farms_7to30", "farms_under7"]

# 원본 시도 약칭 → region_code_map.sido_name 후보 (2026 명칭 변경·통합 포함)
SIDO_ALIAS = {
    "서울": ["서울특별시"], "부산": ["부산광역시"], "대구": ["대구광역시"], "인천": ["인천광역시"],
    "광주": ["광주광역시", "전남광주통합특별시"], "대전": ["대전광역시"], "울산": ["울산광역시"],
    "세종": ["세종특별자치시"], "경기": ["경기도"], "강원": ["강원도", "강원특별자치도"],
    "충북": ["충청북도"], "충남": ["충청남도"], "전북": ["전라북도", "전북특별자치도"],
    "전남": ["전라남도", "전남광주통합특별시"], "경북": ["경상북도"], "경남": ["경상남도"],
    "제주": ["제주특별자치도"],
}


def q(v):
    return "'" + str(v).replace("'", "''") + "'"


def _fetch_path(path: str, key: str) -> list:
    rows, page = [], 1
    while True:
        r = requests.get(BASE + path, timeout=30, params={
            "serviceKey": key, "page": page, "perPage": 1000, "returnType": "JSON"})
        if r.status_code != 200:
            sys.exit(f"API 오류 HTTP {r.status_code}: {r.text[:300].replace(key, '***')}")
        body = r.json()
        rows += body.get("data", [])
        if page * 1000 >= body.get("totalCount", 0):
            break
        page += 1
    # 컬럼명 공백 제거 ("(두 수)" → "(두수)" 등 파일마다 표기 차이)
    return [{k.replace(" ", ""): v for k, v in x.items()} for x in rows]


def fetch_api() -> pd.DataFrame:
    """경로(파일 버전)가 여러 개면 모두 받아서 최신 연도가 가장 큰 것을 사용."""
    load_dotenv()
    key = unquote((os.environ.get("PUBLIC_DATA_API_KEY") or os.environ["DATA_GO_KR_KEY"]).strip())
    spec = requests.get(SWAGGER, timeout=20).json()
    best = None
    for path in sorted(spec["paths"]):
        rows = _fetch_path(path, key)
        years = [int(x["년도"]) for x in rows if str(x.get("년도", "")).strip().isdigit()]
        info = f"{len(rows)}행, 연도 {min(years)}~{max(years)}" if years else f"{len(rows)}행"
        print(f"API 경로 {path}: {info}")
        if years and (best is None or max(years) > best[0]):
            best = (max(years), path, rows)
    if best is None:
        sys.exit("API에서 데이터를 받지 못함")
    print(f"사용: {best[1]} (최신 연도 {best[0]})")
    df = pd.DataFrame(best[2])
    df = df.rename(columns={d: c for c, d in COLS})
    return df


args = [a for a in sys.argv[1:]]
want_years = None
if "--years" in args:
    i = args.index("--years")
    want_years = [int(y) for y in args[i + 1].split(",")]
    del args[i:i + 2]
use_api = (not args) or args[0] == "--api"
if use_api:
    args = args[1:] if args else []
    df = fetch_api()
else:
    df = pd.read_csv(args.pop(0), encoding="cp949")
out = args[0] if args else "load_farm_scale_statistics.sql"

df.columns = [str(c).replace(" ", "") for c in df.columns]
missing = [c for c, _ in COLS if c not in df.columns]
if missing:
    sys.exit(f"원본 컬럼이 다름: {missing}")
df = df.rename(columns=dict(COLS))[[d for _, d in COLS]]
for c in df.columns:
    if c not in ("breed", "province", "city_county"):
        df[c] = pd.to_numeric(df[c]).astype(int)   # API가 문자열로 줘도 숫자로

FROM_YEAR = 2023   # 이 연도부터 적재 (서비스는 최근 발생·최신 통계만 씀)
if want_years is None:
    want_years = sorted(y for y in df["year"].unique() if y >= FROM_YEAR)
df = df[df["year"].isin(want_years)]
if df.empty:
    sys.exit(f"{want_years} 연도 데이터 없음")
print("넣을 연도:", [int(y) for y in want_years])

bad = df[df[FARM_BANDS].sum(axis=1) != df["total_farms"]]
if len(bad):
    sys.exit(f"구간 호수 합 ≠ 전체호수 행 {len(bad)}개 → 중단\n{bad.head().to_string()}")
breeds = df["breed"].unique().tolist()

alias_rows = ",\n  ".join(f"({q(k)}, {q(v)})" for k, vs in SIDO_ALIAS.items() for v in vs)
db_cols = ", ".join(d for _, d in COLS)
values = []
for r in df.itertuples(index=False):
    d = r._asdict()
    vals = [str(int(d[c])) if c not in ("breed", "province", "city_county") else q(d[c])
            for _, c in COLS]
    vals += [q(f"{int(d['year'])}.01"), "now()"]
    values.append("(" + ", ".join(vals) + ")")

sql = f"""-- farm_scale_statistics 적재 (data.go.kr 15147310) — 원본 {len(df)}행, 연도 {df.year.min()}~{df.year.max()}
-- DBeaver에서 전체 실행(Alt+X). 다시 실행해도 같은 결과.
BEGIN;

DELETE FROM farm_scale_statistics WHERE breed IN ({", ".join(q(b) for b in breeds)})
  AND year IN ({", ".join(str(int(y)) for y in want_years)});

INSERT INTO farm_scale_statistics ({db_cols}, reference_ym, collected_at) VALUES
{",\n".join(values)};

-- region_code 채우기 (region_code_map 기준, 현행 코드 우선)
WITH alias(province, sido_name) AS (VALUES
  {alias_rows}
),
cand AS (
  SELECT DISTINCT ON (s.farm_scale_statistics_id)
         s.farm_scale_statistics_id, m.region_code
  FROM farm_scale_statistics s
  JOIN alias a ON a.province = s.province
  JOIN region_code_map m ON m.sido_name = a.sido_name
  WHERE s.region_code IS NULL
    AND (
      -- 광역시·세종 (시군 = 시도): 시도 코드. 광주는 통합 시도 전체로 올리지 않음
      --   (세종은 코드표에 시도 행 없이 시군구 행 3611000000, sigungu_name NULL 로만 있음)
      (s.province = s.city_county
         AND (m.region_level = 'sido' OR (m.region_level = 'sigungu' AND m.sigungu_name IS NULL))
         AND NOT (s.province = '광주' AND m.sido_name = '전남광주통합특별시'))
      -- 일반 시·군: 시군구 코드 (읍면동 아닌 행)
      OR (s.province <> s.city_county AND m.region_level = 'sigungu'
         AND m.sigungu_name = s.city_county AND m.emd_name IS NULL)
    )
  ORDER BY s.farm_scale_statistics_id, m.is_active DESC, (m.region_level = 'sido') DESC, m.region_code
)
UPDATE farm_scale_statistics s SET region_code = c.region_code
FROM cand c WHERE c.farm_scale_statistics_id = s.farm_scale_statistics_id;

COMMIT;

-- 확인 1: 연도별 행 수 / region_code 없는 행 수
SELECT year, count(*) AS rows, count(*) FILTER (WHERE region_code IS NULL) AS no_code
FROM farm_scale_statistics GROUP BY year ORDER BY year;

-- 확인 2: region_code 못 찾은 지역 (최신 연도)
SELECT province, city_county FROM farm_scale_statistics
WHERE region_code IS NULL AND year = (SELECT max(year) FROM farm_scale_statistics)
ORDER BY 1, 2;
"""
with open(out, "w", encoding="utf-8") as f:
    f.write(sql)
print(f"SQL 생성: {out} ({len(df)}행, 연도 {df.year.min()}~{df.year.max()}, 품종 {breeds})")
