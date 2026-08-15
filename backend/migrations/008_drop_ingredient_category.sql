-- ============================================================
-- 008_drop_ingredient_category.sql
-- 删除 ingredients.category 字符串列（食材分类只保留 category_id 外键）
--
-- 背景：旧版同时保留 category（字符串）与 category_id（外键）两个分类字段，
-- 分类体系重构后以 category_id 为唯一事实来源，该字符串列冗余。
--
-- 发布顺序（两步发布，代码先行）：
--   1. 先部署去掉 Ingredient.category 引用的代码（Step A），确认后端正常；
--   2. 再在数据库上手动执行本脚本（Step B）。
--   严禁先落列后改码（运行期 ColumnError）。
--
-- 目标数据库：MariaDB（生产库）。
-- 执行：mysql -u cook -p -h 192.168.31.146 -P 3307 cook < 008_drop_ingredient_category.sql
-- ============================================================

SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;

ALTER TABLE ingredients
    DROP COLUMN IF EXISTS category;
