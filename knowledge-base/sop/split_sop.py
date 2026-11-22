"""SOP PDF → 조항 단위 행(CSV) 분할. 원문 문장은 그대로, 줄바꿈만 이어 붙임.

사용법:
    pdftotext "구제역SOP.pdf" fmd_raw.txt          # 페이지 구분(\\f) 유지되는 기본 모드
    python knowledge-base/sop/split_sop.py fmd fmd_raw.txt sop/fmd_clauses.csv

- 범위: SECTIONS (기획서 표17 활용 항목: 의심증상·예찰·신고·이동/출입 제한·소독)
- 빼는 장: 위기경보, 일시이동중지, 살처분, 역학조사, 초소 운영, 도축 (기관 행정 절차)
- 제거: 쪽 번호, 옆 탭 글자(세로 장 제목), ⚫
- 자르는 기준: "1.", "1.1", "2.1.2" 같은 번호 줄. 너무 짧으면 다음 조항과 합침, 너무 길면 문단 단위로 나눔
"""
import csv
import re
import sys

DOCS = {
    "fmd": {
        "source_doc": "구제역 긴급행동지침(SOP)",
        "revised_at": "2026-05-06",
        "disease": "FMD",
        # (조항 이름, 시작 PDF쪽, 시작 제목 정규식, 끝 PDF쪽, 끝 제목 정규식 | None=끝쪽 전체)
        "sections": [
            ("제1장 구제역 개요", 9, r"1\s*정\s*의", 21, r"구제역 상황별 조치사항"),
            ("제4장 1. 의심축 신고 및 의사환축 발생 시 조치사항", 69, r"1 의심축 신고 및 의사환축 발생 시 조치사항", 76, r"2 구제역 임상관찰 및 예찰 요령"),
            ("제4장 2. 구제역 임상관찰 및 예찰 요령", 76, r"2 구제역 임상관찰 및 예찰 요령", 79, r"3 시료채취.*"),
            ("제4장 4. 의심축 발견 축산관련 종사자의 조치사항", 83, r"4 의심축 발견 축산관련 종사자의 조치 ?사항", 86, r"5 초동방역팀 운영 요령"),
            ("제4장 9. 이동제한 요령", 102, r"9 이동제한 요령", 105, r"10 살처분.*"),
            ("제4장 11. 발생농장의 청소·세척 및 소독 요령", 111, r"11 발생농장의 청소.*", 113, r"12 역학조사.*"),
            ("제4장 16. 이동제한 기간 중 원유·사료·분뇨 관리 요령", 135, r"16 이동제한 기간 중 원유.*", 142, r"17 지정도축장.*"),
            ("별표 3 소독제의 종류 및 적용방법", 294, r"소독제의 종류 및 적용방법", 298, r"축산농장 준수사항"),
            ("별표 4 축산농장 준수사항", 298, r"축산농장 준수사항", 305, r"축산관련 종사자의 준수사항"),
            ("별표 5 축산관련 종사자의 준수사항", 305, r"축산관련 종사자의 준수사항", 308, r"축산관련 작업장 및 경영자 조치사항"),
        ],
    },
}

NUM = re.compile(r"^(\d{1,2}(\.\d{1,2})*\.?)\s+\S")   # 1.  1.1  2.1.2 (3자리 이상 = 쪽번호·OCR 잡음)
JUNK = re.compile(r"^(⚫|\d{1,3}|[Ⅰ-Ⅻ]|[가-힣]|별표\s*\d+|부록|<[^>]*>"
                  r"|\d{1,3}\s*⚫.*긴급행동지침\(SOP\)|.*긴급행동지침\(SOP\)\s*⚫\s*\d{1,3})$")   # 쪽 머리말
MIN_LEN, MAX_LEN = 80, 1500


def lines_of(page_text):
    out = []
    for ln in page_text.split("\n"):
        s = ln.strip()
        if not s or JUNK.match(s):
            continue
        out.append(s)
    return out


def slice_section(pages, sp, spat, ep, epat):
    """(쪽, 줄) 목록 — 시작 제목 줄부터 끝 제목 줄 직전까지"""
    rows, on = [], False
    for pno in range(sp, ep + 1):
        for s in lines_of(pages[pno - 1]):
            if not on and pno == sp and re.fullmatch(spat, s):
                on = True
            elif on and pno == ep and epat and re.fullmatch(epat, s):
                return rows
            if on:
                rows.append((pno, s))
    return rows


def join(lines):
    # 한글 줄바꿈은 공백으로 이어 붙임 (원문 단어는 바꾸지 않음)
    return re.sub(r"\s+", " ", " ".join(lines)).strip()


def chunk(rows):
    chunks, cur = [], []
    for pno, s in rows:
        if NUM.match(s) and cur:
            chunks.append(cur)
            cur = []
        cur.append((pno, s))
    if cur:
        chunks.append(cur)
    merged = []
    for c in chunks:                     # 짧은 조항(장 제목 등)은 다음 조항 앞에 붙임
        if merged and len(join(s for _, s in merged[-1])) < MIN_LEN:
            merged[-1] += c
        else:
            merged.append(c)
    out = []
    for c in merged:                     # 긴 조항은 줄 단위로 MAX_LEN 이하로 나눔
        part = []
        for item in c:
            if part and len(join(s for _, s in part + [item])) > MAX_LEN:
                out.append(part)
                part = []
            part.append(item)
        out.append(part)
    return out


def main():
    key, raw, out = sys.argv[1], sys.argv[2], sys.argv[3]
    doc = DOCS[key]
    pages = open(raw, encoding="utf-8").read().split("\f")
    rows = []
    for name, sp, spat, ep, epat in doc["sections"]:
        sec = slice_section(pages, sp, spat, ep, epat)
        if not sec:
            sys.exit(f"시작 제목을 못 찾음: {name}")
        for i, c in enumerate(chunk(sec), 1):
            text = join(s for _, s in c)
            first = c[0][1]
            m = NUM.match(first)
            rows.append({
                "kind": "clause", "disease": doc["disease"], "stage": "",
                "display_order": len(rows) + 1, "text": text,
                "source_doc": doc["source_doc"],
                "clause": f"{name}" + (f" {m.group(1).rstrip('.')}" if m else "")
                          + f" (PDF p.{c[0][0]}" + (f"~{c[-1][0]}" if c[-1][0] != c[0][0] else "") + ")",
                "revised_at": doc["revised_at"],
                "part_code": "", "photo_part": "", "yes_required_parts": "", "note": "",
            })
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    lens = [len(r["text"]) for r in rows]
    print(f"{out}: {len(rows)}행, 글자 수 최소 {min(lens)} / 평균 {sum(lens)//len(lens)} / 최대 {max(lens)}")


if __name__ == "__main__":
    main()
