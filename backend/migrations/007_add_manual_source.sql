-- ============================================================
-- 007_add_manual_source.sql
-- AI 采集手动模式：记录用户粘贴的来源 URL 与正文（登录墙/反爬站点如小红书）
-- 目标数据库：MariaDB（生产库），应用层 create_all 只建新表不改旧表，
-- 因此本脚本需在已有数据库上手动执行一次。
-- 执行：mysql -u cook -p -h 192.168.31.146 -P 3307 cook < 007_add_manual_source.sql
-- ============================================================

SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;

ALTER TABLE ingestion_jobs
    ADD COLUMN IF NOT EXISTS manual_url VARCHAR(500) NULL,
    ADD COLUMN IF NOT EXISTS manual_content TEXT NULL;
