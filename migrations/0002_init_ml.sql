-- 0002_init_ml.sql
-- 학습 데이터 메타 (명세서 aihub_behavior_label · part_image_dataset, REQ-DATA-10)
-- 운영 테이블과 FK로 연결하지 않는다. 원본 파일은 Object Storage aihub/, part/ 경로.

BEGIN;

CREATE TABLE dataset_version (
  dataset_version_id   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  dataset_name         VARCHAR(100) NOT NULL,        -- aihub_behavior|part_image
  version              VARCHAR(20)  NOT NULL,
  preprocessing_config JSONB,
  storage_prefix       VARCHAR(200),                 -- part/ · aihub/ 하위 경로
  mlflow_run_id        VARCHAR(64),
  created_at           TIMESTAMPTZ  NOT NULL DEFAULT now(),
  CONSTRAINT uk_dataset_name_version UNIQUE (dataset_name, version)
);

CREATE TABLE part_image_dataset (
  part_image_dataset_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  dataset_version_id   BIGINT REFERENCES dataset_version (dataset_version_id),
  file_path            VARCHAR(500) NOT NULL,        -- part/
  part_label           VARCHAR(30)  NOT NULL,        -- head_mouth|udder_teat|hoof|body_side_skin
  source               VARCHAR(100),                 -- FMD Cattle | Cattle side view and back view
  split                VARCHAR(10),                  -- train|val|test
  license              VARCHAR(100)
);
CREATE INDEX idx_part_dataset ON part_image_dataset (dataset_version_id);

CREATE TABLE aihub_behavior_label (
  aihub_behavior_label_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  dataset_version_id   BIGINT REFERENCES dataset_version (dataset_version_id),
  video_id             VARCHAR(100) NOT NULL,
  frame_no             INT,
  file_path            VARCHAR(500) NOT NULL,        -- aihub/
  action_name          VARCHAR(50),
  behavior_label       VARCHAR(20),                  -- stand|lie|eat
  bbox                 JSONB,
  split                VARCHAR(10)
);
CREATE INDEX idx_aihub_dataset ON aihub_behavior_label (dataset_version_id);
CREATE INDEX idx_aihub_video   ON aihub_behavior_label (video_id, frame_no);

COMMIT;
