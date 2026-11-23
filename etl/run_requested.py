"""어드민 [지금 수집] 요청 실행 (서버 예약으로 5분마다).

실행: python etl/run_requested.py
- etl_job_run 에서 status = 'requested' 인 작업을 찾아 그 작업의 수집 스크립트를 실행
- 수집 스크립트(run_job)가 requested 행을 이어받아 running → success/failed 로 바꿈
- 이미 같은 작업이 running 이면 이번에는 건너뜀 (다음 확인 때 실행)
- 모르는 작업 이름은 failed 로 바꿔서 대기 상태로 남지 않게 함
- 실행한 작업 중 하나라도 실패하면 종료 코드 1
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import connect_db  # noqa: E402

SCRIPTS = {   # etl_job_run.job → 수집 스크립트
    "outbreak": "outbreak/collect.py",
    "disinfection_facility": "disinfection_facility/collect.py",
    "farm_scale": "farm_scale/collect.py",
}


def main():
    with connect_db(autocommit=True) as db:
        jobs = [r[0] for r in db.execute(
            "SELECT DISTINCT job FROM etl_job_run WHERE status = 'requested' ORDER BY job")]
        running = {r[0] for r in db.execute(
            "SELECT DISTINCT job FROM etl_job_run WHERE status = 'running'")}
        for job in [j for j in jobs if j not in SCRIPTS]:
            db.execute("UPDATE etl_job_run SET status = 'failed', finished_at = now(), "
                       "error = '알 수 없는 작업' WHERE job = %s AND status = 'requested'", (job,))
            print("알 수 없는 작업 → failed:", job)

    if not jobs:
        print("요청 없음")
        return 0
    failed = 0
    for job in jobs:
        if job not in SCRIPTS:
            continue
        if job in running:
            print("실행 중이라 건너뜀:", job)
            continue
        print("실행:", job)
        code = subprocess.run([sys.executable, os.path.join(HERE, SCRIPTS[job])], cwd=os.getcwd()).returncode
        failed += code != 0
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
