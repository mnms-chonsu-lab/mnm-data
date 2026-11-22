"""가축 질병 발생 정보 수집 → DB outbreak_info (일 1회).

출처: 농림축산식품 공공데이터포털 「가축질병발생정보」 오픈 API
      (TI_QIA_LVSTCK_DISOCNC_INFO, Grid_20151204000000000316_1, 제공 농림축산검역본부)
실행: python etl/outbreak/collect.py
- 전체 행을 받아 축종(LVSTCKSPC_NM)이 "소-한우"인 행만 적재 (명세 DATA-02 "소(한우) 데이터만")
- 같은 발생 번호(ICTSD_OCCRRNC_NO)가 있으면 덮어씀
- 하나라도 실패하면 전체 취소 → 직전 데이터 유지, etl_job_run failed + 웹훅 알림
- 농장명(FARM_NM)은 개인정보가 섞여 있어 DB·원본 저장 모두 넣지 않음
- 법정동 코드: ① 현재 코드표에 있으면 그대로 ② 공식 변경표(옛 코드 → 새 코드) ③ 농장 소재지 이름으로 찾음
"""
import json
import os
import sys
from collections import Counter
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import load_official, load_region_index, mafra_fetch_all, match_name, run_job, upload_raw  # noqa: E402

JOB = "outbreak"
GRID = "Grid_20151204000000000316_1"
LIVESTOCK = "소-한우"   # 적재할 축종 (LVSTCKSPC_NM 값)


def to_date(v):
    v = str(v or "").strip()
    return datetime.strptime(v, "%Y%m%d").date() if v else None


def s(v):
    v = str(v if v is not None else "").strip()
    return v or None


def work(conn):
    rows, pages = mafra_fetch_all(GRID)
    print("API 전체:", len(rows), "건")
    species = Counter(s(r.get("LVSTCKSPC_NM")) for r in rows)
    print("축종별 건수 (상위 10):", species.most_common(10))

    for p in pages:
        for r in p.get("row") or []:
            r.pop("FARM_NM", None)
    upload_raw(json.dumps(pages, ensure_ascii=False).encode("utf-8"), "outbreak_info",
               f"{GRID}_{datetime.now():%H%M%S}.json")

    target = [r for r in rows if s(r.get("LVSTCKSPC_NM")) == LIVESTOCK]
    print(f"적재 대상 ({LIVESTOCK}):", len(target), "건")

    by_name, codes = load_region_index(conn)
    off_code, off_name = load_official()
    print("공식 변경표:", len(off_code), "건" if off_code else "건 (official_map.csv 없음 → ②단계 건너뜀)")

    out, stat, unmatched = [], Counter(), 0
    for r in target:
        orig = s(r.get("FARM_LOCPLC_LEGALDONG_CODE")) or ""
        if orig in codes:
            code = orig
            stat["원래 코드 그대로"] += 1
        elif off_code.get(orig) in codes:
            code = off_code[orig]
            stat["공식 변경표"] += 1
        else:
            code, _, _, basis = match_name(r.get("FARM_LOCPLC") or "", by_name, off_name)
            stat["이름으로 찾음: " + basis] += 1
            unmatched += 0 if code else 1
        cnt = r.get("OCCRRNC_LVSTCKCNT")
        out.append((
            s(r.get("ICTSD_OCCRRNC_NO")),
            s(r.get("LKNTS_NM")),
            s(r.get("FARM_LOCPLC")),
            code,
            to_date(r.get("OCCRRNC_DE")),
            s(r.get("LVSTCKSPC_NM")),
            int(cnt) if str(cnt or "").strip() else None,
            s(r.get("DGNSS_ENGN_NM")),
            to_date(r.get("CESSATION_DE")),
        ))
    print("법정동 코드 매핑:", dict(stat), "/ 실패", unmatched, "건")

    with conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO outbreak_info
               (ictsd_occrrnc_no, lknts_nm, farm_locplc, region_code, occrrnc_de,
                lvstckspc_nm, occrrnc_lvstckcnt, dgnss_engn_nm, cessation_de, collected_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, now())
               ON CONFLICT (ictsd_occrrnc_no) DO UPDATE SET
                 lknts_nm = EXCLUDED.lknts_nm, farm_locplc = EXCLUDED.farm_locplc,
                 region_code = EXCLUDED.region_code, occrrnc_de = EXCLUDED.occrrnc_de,
                 lvstckspc_nm = EXCLUDED.lvstckspc_nm, occrrnc_lvstckcnt = EXCLUDED.occrrnc_lvstckcnt,
                 dgnss_engn_nm = EXCLUDED.dgnss_engn_nm, cessation_de = EXCLUDED.cessation_de,
                 collected_at = EXCLUDED.collected_at""",
            out,
        )
    return len(out)


if __name__ == "__main__":
    run_job(JOB, work)
