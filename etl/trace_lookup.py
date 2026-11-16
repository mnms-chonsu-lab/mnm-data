"""쇠고기 이력정보 조회 (REQ-DATA-11) — 공공데이터포털 15056898.

입력: 귀표 번호 12자리 → 출력(고정):
    { tag_no, breed, sex, birth_date, vaccine_last_date, vaccine_last_order, farm_no, checked_at }
실패: CATTLE-NOTFOUND(결과 없음), TRACE-API-FAIL(오류·한도 초과)

- 인증키: .env 의 PUBLIC_DATA_API_KEY (없으면 DATA_GO_KR_KEY). Encoding 키 그대로 넣어도 됨
- 같은 번호는 하루 캐시 (trace_lookups). 개발계정 한도 1,000회/일
- 농장명·농장주소(farmNm, farmAddr)는 저장하지 않음 → response 에는 아래 고정 필드만 JSON 으로 저장

사용법(확인용):
    python etl/trace_lookup.py 002046636437           # DB 캐시 사용
    python etl/trace_lookup.py 002046636437 --no-db   # API 응답만 확인
"""
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from urllib.parse import unquote


import requests
from dotenv import load_dotenv

load_dotenv()
URL = "http://data.ekape.or.kr/openapi-data/service/user/mtrace/breeding/cattle"
COUNTRY = "410"            # 샘플 410002046636437 기준 (활용가이드로 재확인)
CACHE_TTL = timedelta(days=1)


class TraceError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code   # CATTLE-NOTFOUND | TRACE-API-FAIL


def _norm(tag_no: str) -> str:
    digits = "".join(c for c in tag_no if c.isdigit())
    if len(digits) == 12:
        return digits
    if len(digits) == 15 and digits.startswith(COUNTRY):
        return digits[3:]
    raise TraceError("CATTLE-NOTFOUND")


def _fmt_date(v):
    v = (v or "").strip()
    return f"{v[:4]}-{v[4:6]}-{v[6:8]}" if len(v) == 8 and v.isdigit() else (v or None)


DEBUG = False


def _debug(msg, key=""):
    if DEBUG:
        print("[debug]", str(msg).replace(key, "***") if key else msg)


def _call_api(tag12: str) -> dict:
    key = unquote((os.environ.get("PUBLIC_DATA_API_KEY") or os.environ["DATA_GO_KR_KEY"]).strip())
    try:
        r = requests.get(URL, params={"serviceKey": key, "cattleNo": COUNTRY + tag12},
                         timeout=10)
        _debug(f"HTTP {r.status_code}", key)
        # 농가 개인정보(farmNm·farmAddr)는 화면에도 가림
        _debug(re.sub(r"<(farmNm|farmAddr)>[^<]*</", r"<\1>***</", r.text[:1500]), key)
        r.raise_for_status()
        root = ET.fromstring(r.content)
    except Exception as e:
        _debug(repr(e), key)
        raise TraceError("TRACE-API-FAIL")
    code = root.findtext(".//resultCode")
    if code not in (None, "00"):
        raise TraceError("TRACE-API-FAIL")
    # 응답에 item 이 여러 개일 수 있음(정보 구분별) → 필요한 필드를 처음 나온 값으로 채움
    want = ["lsTypeNm", "sexNm", "birthYmd", "vaccineLastinjectionYmd",
            "vaccineLastinjectionOrder", "farmNo"]
    got = {}
    for item in root.iter("item"):
        for f in want:
            v = item.findtext(f)
            if v and f not in got:
                got[f] = v.strip()
    if not got:
        raise TraceError("CATTLE-NOTFOUND")
    return {
        "tag_no": tag12,
        "breed": got.get("lsTypeNm"),
        "sex": got.get("sexNm"),
        "birth_date": _fmt_date(got.get("birthYmd")),
        "vaccine_last_date": _fmt_date(got.get("vaccineLastinjectionYmd")),
        "vaccine_last_order": (re.sub(r"\D", "", got.get("vaccineLastinjectionOrder") or "")
                               or None),   # "4 차" → "4"
        "farm_no": got.get("farmNo"),
    }


def lookup(tag_no: str, conn) -> dict:
    tag12 = _norm(tag_no)
    now = datetime.now(timezone.utc)
    with conn.cursor() as cur:
        cur.execute("SELECT response, status, checked_at FROM trace_lookups "
                    "WHERE ear_tag_no=%s", (tag12,))
        row = cur.fetchone()
    if row and now - row[2] < CACHE_TTL:
        if row[1] == "ok":
            return json.loads(row[0])
        if row[1] == "notfound":
            raise TraceError("CATTLE-NOTFOUND")
        # fail 은 캐시하지 않고 다시 호출

    try:
        out = _call_api(tag12)
        status, err = "ok", None
    except TraceError as e:
        out, status, err = None, ("notfound" if e.code == "CATTLE-NOTFOUND" else "fail"), e
    if out:
        out["checked_at"] = now.isoformat()
    with conn, conn.cursor() as cur:
        cur.execute(
            """INSERT INTO trace_lookups (ear_tag_no, response, status, checked_at)
               VALUES (%s,%s,%s,%s)
               ON CONFLICT (ear_tag_no) DO UPDATE
               SET response=EXCLUDED.response, status=EXCLUDED.status,
                   checked_at=EXCLUDED.checked_at""",
            (tag12, json.dumps(out, ensure_ascii=False) if out else None, status, now))
    if err:
        raise err
    return out


if __name__ == "__main__":
    if "--no-db" in sys.argv:   # API 응답만 확인 (DB 저장·캐시 없음, 응답 원문 출력)
        DEBUG = True
        try:
            out = _call_api(_norm(sys.argv[1]))
            print(json.dumps(out, ensure_ascii=False, indent=2))
        except TraceError as e:
            print(e.code)
        sys.exit()
    import psycopg2
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        print(json.dumps(lookup(sys.argv[1], conn), ensure_ascii=False, indent=2))
    except TraceError as e:
        print(e.code)
    finally:
        conn.close()
