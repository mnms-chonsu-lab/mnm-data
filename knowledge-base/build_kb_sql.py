"""knowledge-base CSV 여러 개 → biosecurity_rule 적재 SQL (status='draft'). DBeaver에서 실행.

사용법:
    python knowledge-base/build_kb_sql.py 출력.sql CSV1 [CSV2 ...]

- 같은 (kind, source_doc) 의 draft 행만 지우고 다시 넣음 → 재실행 안전, 검수·게시 행은 안 건드림
"""
import csv
import sys


def q(v):
    return "NULL" if v in ("", None) else "'" + str(v).replace("'", "''") + "'"


out, srcs = sys.argv[1], sys.argv[2:]
rows = []
for p in srcs:
    rows += list(csv.DictReader(open(p, encoding="utf-8-sig")))
pairs = sorted({(r["kind"], r["source_doc"]) for r in rows})

sql = ["-- biosecurity_rule 적재 (status='draft') — " + ", ".join(srcs),
       "BEGIN;"]
for k, d in pairs:
    sql.append(f"DELETE FROM biosecurity_rule WHERE status='draft' AND kind={q(k)} AND source_doc={q(d)};")
for r in rows:
    y = q(r.get("yes_required_parts", ""))
    y = y + "::jsonb" if y != "NULL" else y
    rev = q(r["revised_at"]) + ("::date" if r["revised_at"] else "")
    sql.append(
        "INSERT INTO biosecurity_rule (kind, disease, stage, text, source_doc, clause, revised_at, status, "
        "display_order, yes_required_parts, part_code, photo_part) VALUES ("
        + ", ".join([q(r["kind"]), q(r["disease"]), q(r["stage"]), q(r["text"]), q(r["source_doc"]),
                     q(r["clause"]), rev, "'draft'", r["display_order"] or "NULL", y,
                     q(r.get("part_code", "")), q(r.get("photo_part", ""))]) + ");")
sql += ["COMMIT;",
        "SELECT kind, source_doc, count(*) FROM biosecurity_rule WHERE status='draft' "
        "GROUP BY 1, 2 ORDER BY 1, 2;"]
open(out, "w", encoding="utf-8").write("\n".join(sql) + "\n")
print(f"{out}: {len(rows)}행")
