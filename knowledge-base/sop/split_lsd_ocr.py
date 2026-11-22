"""럼피스킨 SOP(2024.7.19) — PDF 글자 추출이 깨져 OCR(tesseract kor, 300dpi) 결과로 조항 분할.
OCR 오탈자 가능 → clause 에 [OCR·원문대조 필요] 표시. 게시 전 PDF 원문과 대조 필수.

사용법:
    (페이지별 OCR 결과 p{PDF쪽}.txt 가 있는 폴더)
    python knowledge-base/sop/split_lsd_ocr.py OCR폴더 sop/lsd_clauses.csv

범위(기획서 표17: 의심증상·신고·출입통제·소독·매개곤충 방제). 2026 제2종 전환으로 바뀐
방역지역 이동제한·일시이동중지·살처분 관련 장은 넣지 않음.
"""
import csv
import re
import sys

from split_sop import chunk, join, NUM

SOURCE, REV = "럼피스킨 긴급행동지침(SOP)", "2024-07-19"
SECTIONS = [  # (조항 이름, PDF 시작쪽, 끝쪽)
    ("제1장 럼피스킨이란", 6, 12),
    ("제4장 1. 의심축 신고 및 의사환축 발생 시 조치사항", 35, 40),
    ("제4장 2. 의심축을 발견한 축산관련 종사자의 조치사항", 41, 43),
    ("제4장 8. 발생농장 등의 청소·세척 및 소독 요령", 97, 103),
    ("제4장 9. 소독제의 종류 및 적용 방법", 106, 107),
    ("제4장 10. 럼피스킨 매개곤충 방제요령", 108, 117),
]
JAMO = re.compile(r"[ㄱ-ㅎㅏ-ㅣ]")


def clean(ln):
    s = ln.strip()
    if not s or re.fullmatch(r"-\s*\d+\s*-", s):          # 쪽 번호
        return None
    body = re.sub(r"^[ㅇ○●◦\-\*※▷]\s*", "", s)            # 글머리표는 허용
    if len(body) < 2 or len(JAMO.findall(body)) / len(body) > 0.2:   # OCR 찌꺼기 줄
        return None
    return s


def main():
    folder, out = sys.argv[1], sys.argv[2]
    rows = []
    for name, sp, ep in SECTIONS:
        sec = []
        for p in range(sp, ep + 1):
            for ln in open(f"{folder}/p{p}.txt", encoding="utf-8"):
                s = clean(ln)
                if s:
                    sec.append((p, s))
        for c in chunk(sec):
            m = NUM.match(c[0][1])
            text = join(s for _, s in c)
            flag = " [2026 제2종 전환 전 내용]" if "제1종" in text else ""
            rows.append({
                "kind": "clause", "disease": "LSD", "stage": "", "display_order": len(rows) + 1,
                "text": text, "source_doc": SOURCE,
                "clause": f"{name}" + (f" {m.group(1).rstrip('.')}" if m else "")
                          + f" (PDF p.{c[0][0]}" + (f"~{c[-1][0]}" if c[-1][0] != c[0][0] else "")
                          + ") [OCR·원문대조 필요]" + flag,
                "revised_at": REV, "part_code": "", "photo_part": "", "yes_required_parts": "", "note": "",
            })
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{out}: {len(rows)}행, 2026 전환 전 표시 {sum('전환 전' in r['clause'] for r in rows)}행")


if __name__ == "__main__":
    main()
