-- 0003_biosecurity_rule_embedding.sql
-- 방역지침 RAG용 임베딩 컬럼 (REQ-DATA-05 "명훈님 RAG용 임베딩 인덱스")
-- pgvector 확장이 필요하다. Cloud DB for PostgreSQL에서 확장 사용 가능 여부는 적용 전에 확인한다.
-- 차원 1536은 제안값 (임베딩 모델 확정 후 @parkmyeonghun 확인, 실측으로 조정).

BEGIN;

CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE biosecurity_rule ADD COLUMN embedding vector(1536);

-- 게시된 조항만 검색 대상. 행 수가 적은 동안은 인덱스 없이 순차 검색으로 충분하다(제안).
-- CREATE INDEX idx_rule_embedding ON biosecurity_rule USING hnsw (embedding vector_cosine_ops);

COMMIT;
