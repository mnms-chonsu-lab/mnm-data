"""거점소독시설 수집 → DB disinfection_facility (일 1회).

출처: 농림축산식품 공공데이터포털 「거점소독시설안내」 오픈 API
      (TI_QLA_PSTN_DSNF_FCLT_GUIDANCE, Grid_20220621000000000618_1, 제공 농림축산식품부)
실행: python etl/disinfection_facility/collect.py
- 시설 고유 번호가 없어서 기존 행을 모두 지우고 새로 넣음
- 한 트랜잭션: 실패하면 지운 것도 취소 → 직전 데이터 유지, etl_job_run failed + 웹훅 알림
- API가 0건이거나 일부만 오면 실패로 보고 지우지 않음
- 법정동 코드: 주소(ADDR) 이름으로 찾음
"""
import json
import os
import sys
from collections import Counter
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import load_official, load_region_index, mafra_fetch_all, match_name, run_job, upload_raw  # noqa: E402

JOB = "disinfection_facility"
GRID = "Grid_20220621000000000618_1"


def s(v):
    v = str(v if v is not None else "").strip()
    return v or None


def num(v):
    v = str(v if v is not None else "").strip()
    return float(v) if v else None


def work(conn):
    rows, pages = mafra_fetch_all(GRID)
    print("API 전체:", len(rows), "건")
    upload_raw(json.dumps(pages, ensure_ascii=False).encode("utf-8"), "disinfection_facility",
               f"{GRID}_{datetime.now():%H%M%S}.json")

    by_name, _ = load_region_index(conn)
    _, off_name = load_official()

    out, stat, unmatched = [], Counter(), 0
    for r in rows:
        code, hit, total, basis = match_name(r.get("ADDR") or "", by_name, off_name)
        stat["근거: " + basis] += 1
        if code and hit < total:
            stat["상위 단계로 매핑 (리·동까지 못 찾음)"] += 1
        unmatched += 0 if code else 1
        phone = s(r.get("PIC_TELNO"))
        out.append((
            s(r.get("PSTN_DSNF_PLC_NM")),
            s(r.get("ADDR")),
            s(r.get("OPER_HR")),
            None if phone in (None, "-") else phone,
            num(r.get("LOT")),   # 경도
            num(r.get("LAT")),   # 위도
            code,
        ))
    print("법정동 코드 매핑:", dict(stat), "/ 실패", unmatched, "건")

    with conn.cursor() as cur:
        cur.execute("DELETE FROM disinfection_facility")
        cur.executemany(
            """INSERT INTO disinfection_facility
               (pstn_dsnf_plc_nm, addr, oper_hr, pic_telno, lot, lat, region_code, collected_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, now())""",
            out,
        )
    return len(out)


if __name__ == "__main__":
    run_job(JOB, work)
