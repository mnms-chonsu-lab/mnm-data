"""공공데이터 수집 공통 함수 (DB 접속, 원본 저장, 실행 기록·실패 알림, 법정동 코드 매핑).

환경변수 (.env 또는 서버 환경):
- DB: DATABASE_URL (없으면 DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)
- 원본 저장(선택): S3_ENDPOINT_URL, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, S3_BUCKET_NAME
  (없으면 원본 저장만 건너뜀. 적재는 계속)
- 실패 알림(선택): ALERT_WEBHOOK_URL, ALERT_WEBHOOK_FORMAT(discord|slack, 기본 discord)
  (비어 있으면 화면 출력만)
"""
import json
import os
import re
import sys
import traceback
import urllib.request
from datetime import datetime

import psycopg
from dotenv import load_dotenv

load_dotenv()


# ---------------------------------------------------------------- DB · 원본 저장

def connect_db(autocommit=False):
    url = os.environ.get("DATABASE_URL", "").strip()
    if url:
        return psycopg.connect(url, autocommit=autocommit)
    return psycopg.connect(
        host=os.environ["DB_HOST"], port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ["DB_NAME"], user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"], autocommit=autocommit,
    )


def upload_raw(body: bytes, dataset: str, filename: str):
    """원본을 Object Storage raw/{dataset}/YYYYMMDD/{filename} 에 저장. 설정이 없거나 실패하면 None."""
    bucket = os.environ.get("S3_BUCKET_NAME") or os.environ.get("S3_BUCKET_RAW")
    if not (bucket and os.environ.get("S3_ENDPOINT_URL") and os.environ.get("AWS_ACCESS_KEY_ID")):
        print("원본 저장: 건너뜀 (Object Storage 설정 없음)")
        return None
    try:
        import boto3
        from botocore.config import Config
        s3 = boto3.client(
            "s3",
            endpoint_url=os.environ["S3_ENDPOINT_URL"],
            region_name=os.environ.get("AWS_REGION") or os.environ.get("S3_REGION") or "kr-standard",
            aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
            config=Config(request_checksum_calculation="when_required",
                          response_checksum_validation="when_required"),
        )
        key = f"raw/{dataset}/{datetime.now():%Y%m%d}/{filename}"
        s3.put_object(Bucket=bucket, Key=key, Body=body)
        print("원본 저장:", f"{bucket}/{key}")
        return key
    except Exception as e:  # noqa: BLE001 — 원본 저장 실패로 적재를 멈추지 않음
        print(f"원본 저장 실패 (적재는 계속): {type(e).__name__}")
        return None


# ---------------------------------------------------------------- 농림축산식품 공공데이터포털 오픈 API

MAFRA_BASE = "http://211.237.50.150:7080/openapi"
PAGE_SIZE = 1000


class CollectError(Exception):
    """수집 실패 (원인 문구에 인증키를 넣지 않음)."""


def mafra_fetch_all(grid_id: str, timeout: float = 30):
    """Grid API 전체 행을 1000건씩 받아 (행 목록, 원본 응답 목록) 반환.

    받은 건수가 totalCnt 와 다르면 실패로 본다 (일부만 받은 데이터로 덮어쓰지 않기 위해).
    """
    key = os.environ.get("MAFRA_API_KEY", "").strip()
    if not key:
        raise CollectError("MAFRA_API_KEY 없음")
    rows, pages, start, total = [], [], 1, None
    while total is None or start <= total:
        end = start + PAGE_SIZE - 1
        url = f"{MAFRA_BASE}/{key}/json/{grid_id}/{start}/{end}"
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                raw = r.read()
        except Exception as e:  # noqa: BLE001
            # 예외 문구에 주소(인증키)가 섞일 수 있어 종류와 HTTP 코드만 남긴다
            code = getattr(e, "code", "")
            raise CollectError(f"API 호출 실패 {start}~{end}행 ({type(e).__name__} {code})".strip()) from None
        try:
            data = json.loads(raw)
            if grid_id not in data and "result" in data:   # 인증키 오류 등은 {"result": {...}} 만 옴
                data = {grid_id: data}
            body = data[grid_id]
        except (ValueError, KeyError, TypeError):
            raise CollectError(f"API 응답 형식이 다름 {start}~{end}행: {raw[:200].decode('utf-8', 'replace').replace(key, '***')}") from None
        result = body.get("result", {})
        if result.get("code") != "INFO-000":
            raise CollectError(f"API 오류 {result.get('code')}: {result.get('message')}")
        total = int(body.get("totalCnt") or 0)
        rows += body.get("row") or []
        pages.append(body)
        start = end + 1
        if total == 0:
            break
    if len(rows) != total:
        raise CollectError(f"받은 건수({len(rows)})가 전체 건수({total})와 다름")
    if total == 0:
        raise CollectError("API가 0건을 반환함")
    return rows, pages


# ---------------------------------------------------------------- 실행 기록 · 실패 알림

def send_alert(text: str):
    """#38 감시 프로그램과 같은 웹훅(ALERT_WEBHOOK_URL)으로 보냄. 없으면 화면에만."""
    print(f"[ALERT] {text}", flush=True)
    url = os.environ.get("ALERT_WEBHOOK_URL", "").strip()
    if not url:
        return
    key = "text" if os.environ.get("ALERT_WEBHOOK_FORMAT", "discord") == "slack" else "content"
    try:
        req = urllib.request.Request(url, data=json.dumps({key: text}).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=10).close()
    except Exception as e:  # noqa: BLE001 — 알림 실패로 기록이 멈추면 안 됨
        print(f"웹훅 전송 실패 ({type(e).__name__})", flush=True)


def run_job(job: str, work):
    """etl_job_run 에 running → success/failed 기록. work(conn) 는 적재한 행 수를 반환.

    work 는 하나의 트랜잭션 안에서 돌고, 실패하면 전체 취소 → 직전 데이터 유지.
    실패하면 웹훅 알림 + 종료 코드 1 (스케줄러가 실패를 알 수 있게).
    """
    with connect_db(autocommit=True) as log:
        run_id = log.execute(
            "INSERT INTO etl_job_run (job, started_at, status) VALUES (%s, now(), 'running') "
            "RETURNING etl_job_run_id", (job,)).fetchone()[0]
        try:
            with connect_db() as conn:       # 정상 종료 시 commit, 예외 시 rollback
                n = work(conn)
        except Exception as e:  # noqa: BLE001
            msg = str(e) if isinstance(e, CollectError) else f"{type(e).__name__}: {str(e)[:300]}"
            if not isinstance(e, CollectError):
                traceback.print_exc()
            log.execute("UPDATE etl_job_run SET finished_at = now(), status = 'failed', error = %s "
                        "WHERE etl_job_run_id = %s", (msg[:1000], run_id))
            send_alert(f"🚨 수집 작업 실패: {job} — {msg[:300]} (직전 데이터 유지)")
            print("실패:", msg)
            sys.exit(1)
        log.execute("UPDATE etl_job_run SET finished_at = now(), status = 'success', rows = %s "
                    "WHERE etl_job_run_id = %s", (n, run_id))
        print(f"성공: {job} {n}건")
        return n


# ---------------------------------------------------------------- 법정동 코드 매핑 (11/15 etl_common 그대로)

# 행정구역 개편 전 시도 이름 → 현재 이름 (법정동 코드표 2026-11-14 적재본 기준)
OLD_SIDO = {
    "강원도": "강원특별자치도",
    "전라북도": "전북특별자치도",
    "전라남도": "전남광주통합특별시",
    "광주광역시": "전남광주통합특별시",
}
# 시도가 바뀐 시군구 (2023년 군위군 경북 → 대구)
MOVED_SIGUNGU = {("경상북도", "군위군"): "대구광역시"}
# 이름이 바뀐 읍면 (시군구, 옛 이름) → 새 이름. 2026-11-15 region_code_map 에서 새 이름 확인
RENAMED_EMD = {
    ("여주시", "능서면"): "세종대왕면",
    ("상주시", "사벌면"): "사벌국면",
    ("경주시", "양북면"): "문무대왕면",
    ("군위군", "고로면"): "삼국유사면",
    ("담양군", "남면"): "가사문학면",
    ("성주군", "금수면"): "금수강산면",
    # 아래 4건은 이름이 고유해서, 코드표에 없으면 매핑이 안 될 뿐 잘못 붙지는 않음 (실행 결과로 확인)
    ("양구군", "남면"): "국토정중앙면",
    ("영월군", "중동면"): "산솔면",
    ("청송군", "부동면"): "주왕산면",
    ("홍천군", "동면"): "영귀미면",
}
# 공식 변경표 (행정안전부 "행정기관(행정동) 및 관할구역(법정동) 변경내역" 첨부 엑셀에서 만든 옛 코드 → 새 코드)
OFFICIAL_MAP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "official_map.csv")  # git 제외(*.csv)



class NameIndex(dict):
    """{이름: 코드}. 별칭까지 들어 있고, 코드표 이름 그대로인 것은 .exact 에 따로 둔다."""
    exact = frozenset()


def load_region_index(conn):
    """region_code_map → {전체 이름: 코드}, {코드 집합}.

    현재 이름 외에 별칭도 넣는다 (현재 이름과 겹치지 않고, 가리키는 코드가 하나일 때만):
    - 구가 새로 생긴 시: '경기도 화성시 매송면 천천리' → '경기도 화성시 ○○구 매송면 천천리'
    - 면↔읍 승격: '충청남도 홍성군 홍북면' → '충청남도 홍성군 홍북읍'
    """
    by_name, codes, alias = {}, set(), {}
    with conn.cursor() as cur:
        cur.execute("SELECT region_code, sido_name, sigungu_name, emd_name FROM region_code_map")
        rows = cur.fetchall()
    for code, sido, sgg, emd in rows:
        codes.add(code)
        by_name.setdefault(" ".join(p for p in (sido, sgg, emd) if p), code)
    for code, sido, sgg, emd in rows:
        if not emd:
            continue
        sgg_variants = [sgg]
        if sgg and " " in sgg:
            sgg_variants.append(sgg.split(" ")[0])  # 구 빼기
        emd_tokens = emd.split(" ")
        emd_variants = [emd]
        if emd_tokens[0][-1] in "읍면":
            swapped = emd_tokens[0][:-1] + ("면" if emd_tokens[0][-1] == "읍" else "읍")
            emd_variants.append(" ".join([swapped] + emd_tokens[1:]))
        for s in sgg_variants:
            for e in emd_variants:
                name = " ".join(p for p in (sido, s, e) if p)
                if name not in by_name:
                    alias.setdefault(name, set()).add(code)
    index = NameIndex(by_name)
    index.exact = frozenset(by_name)
    for name, cs in alias.items():
        if len(cs) == 1:
            index[name] = next(iter(cs))
    return index, codes


def normalize_tokens(text):
    """주소·지역명 → 번지 제거 + 옛 시도 이름 교체한 단어 목록."""
    tokens = re.sub(r"\s+", " ", str(text)).strip().split(" ")
    kept = []
    for t in tokens:
        if re.match(r"^(산)?\d", t):  # 번지(0421-0002, 산0141-0023)부터는 버림
            break
        kept.append(t)
    if not kept:
        return kept
    if len(kept) >= 2 and (kept[0], kept[1]) in MOVED_SIGUNGU:
        kept[0] = MOVED_SIGUNGU[(kept[0], kept[1])]
    kept[0] = OLD_SIDO.get(kept[0], kept[0])
    for i in range(1, len(kept) - 1):
        new = RENAMED_EMD.get((kept[i], kept[i + 1]))
        if new:
            kept[i + 1] = new
    return kept


def strip_bunji(text):
    """번지만 떼고 원래 이름 그대로의 단어 목록 (시도 이름도 바꾸지 않음)."""
    tokens = re.sub(r"\s+", " ", str(text)).strip().split(" ")
    kept = []
    for t in tokens:
        if re.match(r"^(산)?\d", t):
            break
        kept.append(t)
    return kept


def load_official():
    """official_map.csv → ({옛 코드: 새 코드}, {옛 이름: 새 코드}). 파일이 없으면 빈 사전."""
    if not os.path.exists(OFFICIAL_MAP_PATH):
        return {}, {}
    import csv
    by_code, by_name = {}, {}
    with open(OFFICIAL_MAP_PATH, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            by_code[r["old_code"]] = r["new_code"]
            by_name.setdefault(" ".join(r["old_name"].split()), set()).add(r["new_code"])
    return by_code, {n: next(iter(c)) for n, c in by_name.items() if len(c) == 1}


def match_name(text, by_name, official_by_name=None):
    """코드 찾기. (코드, 맞은 단어 수, 전체 단어 수, 근거) 반환.

    근거 순서: ① 공식 변경표(옛 이름 그대로) ② 코드표와 글자 그대로 ③ 시도 이름 변경 ④ 추정 규칙 ⑤ 상위 단계
    """
    raw = strip_bunji(text)
    if official_by_name:
        for n in range(len(raw), 2, -1):
            code = official_by_name.get(" ".join(raw[:n]))
            if code:
                return code, n, len(raw), "공식 변경표"
    exact = getattr(by_name, "exact", by_name)
    if " ".join(raw) in exact:
        return by_name[" ".join(raw)], len(raw), len(raw), "코드표와 글자 그대로"
    sido_only = raw[:1] and [OLD_SIDO.get(raw[0], raw[0])] + raw[1:]
    if sido_only and " ".join(sido_only) in exact:
        return by_name[" ".join(sido_only)], len(raw), len(raw), "시도 이름 변경"
    tokens = normalize_tokens(text)
    if " ".join(tokens) in by_name:
        return by_name[" ".join(tokens)], len(tokens), len(tokens), "추정 규칙"
    for n in range(len(tokens) - 1, 0, -1):
        code = by_name.get(" ".join(tokens[:n]))
        if code:
            return code, n, len(tokens), "상위 단계"
    return None, 0, len(tokens), "매핑 실패"
