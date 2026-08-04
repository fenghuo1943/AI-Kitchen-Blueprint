-- ============================================================
-- 004_add_ai_ingestion.sql
-- AI 联网采集菜谱入库：候选/审核表 + 采集任务扩展列
-- 目标数据库：MariaDB（生产库），应用层 create_all 只建新表不改旧表，
-- 因此本脚本需在已有数据库上手动执行一次。
-- 执行：mysql -u cook -p -h 192.168.31.146 -P 3307 cook < 004_add_ai_ingestion.sql
-- ============================================================

SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;
SET FOREIGN_KEY_CHECKS = 0;

-- ---------- ingestion_jobs 补采集任务元信息列 ----------
ALTER TABLE ingestion_jobs
    ADD COLUMN IF NOT EXISTS job_type VARCHAR(20) NOT NULL DEFAULT 'manual' AFTER result_recipe_id;
ALTER TABLE ingestion_jobs
    ADD COLUMN IF NOT EXISTS request_text VARCHAR(500) NULL AFTER job_type;
ALTER TABLE ingestion_jobs
    ADD COLUMN IF NOT EXISTS collection_mode VARCHAR(20) NOT NULL DEFAULT 'topic' AFTER request_text;
ALTER TABLE ingestion_jobs
    ADD COLUMN IF NOT EXISTS target_recipe_id VARCHAR(36) NULL AFTER collection_mode;
ALTER TABLE ingestion_jobs
    ADD COLUMN IF NOT EXISTS max_results INT NOT NULL DEFAULT 5 AFTER target_recipe_id;
ALTER TABLE ingestion_jobs
    ADD COLUMN IF NOT EXISTS candidates_count INT NOT NULL DEFAULT 0 AFTER max_results;
ALTER TABLE ingestion_jobs
    ADD COLUMN IF NOT EXISTS index_status VARCHAR(20) NULL AFTER candidates_count;
ALTER TABLE ingestion_jobs
    ADD COLUMN IF NOT EXISTS reason TEXT NULL AFTER index_status;
ALTER TABLE ingestion_jobs
    ADD CONSTRAINT fk_ingestion_jobs_target FOREIGN KEY (target_recipe_id) REFERENCES recipes(id);

-- ---------- 候选 + 补全目标 + 审核结果 ----------
CREATE TABLE IF NOT EXISTS ingestion_candidates (
    id                    VARCHAR(36)  NOT NULL PRIMARY KEY,
    job_id                VARCHAR(36)  NOT NULL,
    recipe_id             VARCHAR(36)  NOT NULL,
    source_id             VARCHAR(36)  NULL,
    target_recipe_id      VARCHAR(36)  NULL,
    action                VARCHAR(20)  NOT NULL DEFAULT 'pending',
    merge_mode            VARCHAR(20)  NOT NULL DEFAULT 'new',
    dedup_key             VARCHAR(64)  NULL,
    normalized_title      VARCHAR(200) NULL,
    core_ingredients_json TEXT         NULL,
    match_scores_json     TEXT         NULL,
    reason                TEXT         NULL,
    reviewed_by           VARCHAR(100) NULL,
    reviewed_at           DATETIME     NULL,
    created_at            DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at            DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at            DATETIME     NULL,
    KEY idx_candidate_action_created (action, created_at),
    KEY idx_candidate_job (job_id),
    KEY idx_candidate_recipe (recipe_id),
    KEY idx_candidate_target (target_recipe_id),
    KEY idx_candidate_dedup (dedup_key),
    CONSTRAINT fk_candidate_job    FOREIGN KEY (job_id)         REFERENCES ingestion_jobs(id) ON DELETE CASCADE,
    CONSTRAINT fk_candidate_recipe FOREIGN KEY (recipe_id)      REFERENCES recipes(id),
    CONSTRAINT fk_candidate_source FOREIGN KEY (source_id)      REFERENCES recipe_sources(id),
    CONSTRAINT fk_candidate_target FOREIGN KEY (target_recipe_id) REFERENCES recipes(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

SET FOREIGN_KEY_CHECKS = 1;
