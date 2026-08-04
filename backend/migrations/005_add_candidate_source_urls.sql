-- ============================================================
-- 005_add_candidate_source_urls.sql
-- AI 采集候选记录全部参考来源 URL（多来源交叉总结用）
-- 目标数据库：MariaDB（生产库），应用层 create_all 只建新表不改旧表，
-- 因此本脚本需在已有数据库上手动执行一次。
-- 执行：mysql -u cook -p -h 192.168.31.146 -P 3307 cook < 005_add_candidate_source_urls.sql
-- ============================================================

SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;

ALTER TABLE ingestion_candidates
    ADD COLUMN IF NOT EXISTS source_urls_json TEXT NULL AFTER source_id;
