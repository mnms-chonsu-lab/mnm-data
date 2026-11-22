"""사육규모별 농장 통계 수집 → DB farm_scale_statistics (월 1회).

출처: 공공데이터포털 15147310 「가축위생방역지원본부_전국 시군별 한우 사육규모 현황」 오픈 API
실행: python etl/farm_scale/collect.py
- 받기·SQL 만들기는 build_farm_scale_sql.py (PR #5) 를 그대로 씀 (인증키: PUBLIC_DATA_API_KEY)
- 만든 SQL을 한 트랜잭션으로 실행: 실패하면 전체 취소 → 직전 데이터 유지, etl_job_run failed + 웹훅 알림
- 원본 갱신은 연 1회라 매월 받아도 같은 값이면 결과가 같음
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from common import CollectError, run_job  # noqa: E402

JOB = "farm_scale"
BUILD = os.path.join(HERE, "build_farm_scale_sql.py")


def work(conn):
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "farm_scale.sql")
        env = dict(os.environ, PYTHONIOENCODING="utf-8")   # 윈도우에서 한글 출력이 깨지지 않게
        p = subprocess.run([sys.executable, BUILD, "--api", out], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=600, env=env)
        print(p.stdout.strip())
        if p.returncode != 0:
            last = (p.stderr.strip().splitlines() or ["원인 없음"])[-1]
            raise CollectError(f"사육규모 SQL 만들기 실패: {last[:300]}")
        sql = open(out, encoding="utf-8").read()

    # BEGIN/COMMIT 과 뒤쪽 확인용 SELECT 는 빼고, run_job 의 트랜잭션 하나로 실행
    body = sql.split("\nBEGIN;\n", 1)[1].split("\nCOMMIT;\n", 1)[0]
    with conn.cursor() as cur:
        cur.execute(body)
        cur.execute("SELECT count(*), count(*) FILTER (WHERE region_code IS NULL) "
                    "FROM farm_scale_statistics WHERE collected_at = now()")
        n, no_code = cur.fetchone()
    print("적재:", n, "행 / region_code 없음:", no_code, "행")
    if n == 0:
        raise CollectError("적재된 행이 0건")
    return n


if __name__ == "__main__":
    run_job(JOB, work)
