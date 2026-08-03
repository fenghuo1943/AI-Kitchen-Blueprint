-- drop_schema.sql
-- ⚠️ 此操作不可逆，请谨慎执行

SET FOREIGN_KEY_CHECKS = 0;

-- =========================
-- 1️⃣ 删除事件
-- =========================
DROP EVENT IF EXISTS ev_cleanup_deleted_recipes;

-- =========================
-- 2️⃣ 删除触发器
-- =========================
DROP TRIGGER IF EXISTS prevent_delete_default_category;
DROP TRIGGER IF EXISTS prevent_delete_default_ing_category;
DROP TRIGGER IF EXISTS prevent_delete_default_seasoning_category;

-- =========================
-- 3️⃣ 删除关系表（子表）
-- =========================
DROP TABLE IF EXISTS user_daily_recipes;
DROP TABLE IF EXISTS user_history;
DROP TABLE IF EXISTS user_favorites;
DROP TABLE IF EXISTS user_steps;
DROP TABLE IF EXISTS user_recipe_ingredients;
DROP TABLE IF EXISTS user_recipe_seasonings;
DROP TABLE IF EXISTS user_recipe_categories;

-- =========================
-- 4️⃣ 删除实体表
-- =========================
DROP TABLE IF EXISTS user_seasonings;
DROP TABLE IF EXISTS user_ingredients;

-- =========================
-- 5️⃣ 删除分类表
-- =========================
DROP TABLE IF EXISTS user_seasoning_categories;
DROP TABLE IF EXISTS user_ing_categories;
DROP TABLE IF EXISTS user_categories;

-- =========================
-- 6️⃣ 删除主表
-- =========================
DROP TABLE IF EXISTS user_recipes;

SET FOREIGN_KEY_CHECKS = 1;

SELECT 'Schema dropped successfully' AS result;