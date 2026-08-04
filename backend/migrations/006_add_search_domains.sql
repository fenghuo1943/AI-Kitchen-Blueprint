-- ============================================================
-- 006_add_search_domains.sql
-- AI 采集任务记录本次限定搜索的站点域名列表（include_domains）
-- 目标数据库：MariaDB（生产库），应用层 create_all 只建新表不改旧表，
-- 因此本脚本需在已有数据库上手动执行一次。
-- 执行：mysql -u cook -p -h 192.168.31.146 -P 3307 cook < 006_add_search_domains.sql
-- ============================================================

SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;

ALTER TABLE ingestion_jobs
    ADD COLUMN IF NOT EXISTS search_domains_json TEXT NULL;
