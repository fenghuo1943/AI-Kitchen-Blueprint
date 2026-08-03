-- ============================================================
-- 003_fix_zero_datetime.sql
-- 修复历史数据中的零值日期（'0000-00-00 00:00:00' / NULL）
-- 起因：分类等表由 SQLAlchemy create_all 创建时无服务端默认值，
--       002 迁移用原生 INSERT IGNORE 未显式提供时间戳，
--       MariaDB 在非严格模式下回填了零值日期，导致 Pydantic 序列化报错：
--       "Input should be a valid datetime or date, month value is outside expected range of 1-12"
-- 修复：将受影响行的 created_at/updated_at 更新为当前时间（NOW()）。
-- 前置：已同步 002 迁移的显式时间戳写法；003 仅修复存量脏数据，可重复执行。
-- 执行：mysql -u cook -p -h 192.168.31.146 -P 3307 cook < 003_fix_zero_datetime.sql
-- ============================================================

SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 零值日期判断：NULL / '0000-00-00 00:00:00' / '0000-00-00'
-- 覆盖所有使用 TimestampMixin 的表（含历史遗留）。
UPDATE ingredient_categories SET created_at = NOW(), updated_at = NOW()
WHERE created_at IS NULL OR created_at <= '0000-00-00 00:00:00'
   OR updated_at IS NULL OR updated_at <= '0000-00-00 00:00:00';

UPDATE recipe_categories SET created_at = NOW(), updated_at = NOW()
WHERE created_at IS NULL OR created_at <= '0000-00-00 00:00:00'
   OR updated_at IS NULL OR updated_at <= '0000-00-00 00:00:00';

UPDATE seasoning_categories SET created_at = NOW(), updated_at = NOW()
WHERE created_at IS NULL OR created_at <= '0000-00-00 00:00:00'
   OR updated_at IS NULL OR updated_at <= '0000-00-00 00:00:00';

UPDATE seasonings SET created_at = NOW(), updated_at = NOW()
WHERE created_at IS NULL OR created_at <= '0000-00-00 00:00:00'
   OR updated_at IS NULL OR updated_at <= '0000-00-00 00:00:00';

UPDATE recipe_seasonings SET created_at = NOW(), updated_at = NOW()
WHERE created_at IS NULL OR created_at <= '0000-00-00 00:00:00'
   OR updated_at IS NULL OR updated_at <= '0000-00-00 00:00:00';

UPDATE recipe_category_links SET created_at = NOW(), updated_at = NOW()
WHERE created_at IS NULL OR created_at <= '0000-00-00 00:00:00'
   OR updated_at IS NULL OR updated_at <= '0000-00-00 00:00:00';

UPDATE favorites SET created_at = NOW(), updated_at = NOW()
WHERE created_at IS NULL OR created_at <= '0000-00-00 00:00:00'
   OR updated_at IS NULL OR updated_at <= '0000-00-00 00:00:00';

UPDATE recipe_history SET created_at = NOW(), updated_at = NOW()
WHERE created_at IS NULL OR created_at <= '0000-00-00 00:00:00'
   OR updated_at IS NULL OR updated_at <= '0000-00-00 00:00:00';

UPDATE meal_plans SET created_at = NOW(), updated_at = NOW()
WHERE created_at IS NULL OR created_at <= '0000-00-00 00:00:00'
   OR updated_at IS NULL OR updated_at <= '0000-00-00 00:00:00';

UPDATE ingredients SET created_at = NOW(), updated_at = NOW()
WHERE created_at IS NULL OR created_at <= '0000-00-00 00:00:00'
   OR updated_at IS NULL OR updated_at <= '0000-00-00 00:00:00';

UPDATE recipes SET created_at = NOW(), updated_at = NOW()
WHERE created_at IS NULL OR created_at <= '0000-00-00 00:00:00'
   OR updated_at IS NULL OR updated_at <= '0000-00-00 00:00:00';

UPDATE recipe_ingredients SET created_at = NOW(), updated_at = NOW()
WHERE created_at IS NULL OR created_at <= '0000-00-00 00:00:00'
   OR updated_at IS NULL OR updated_at <= '0000-00-00 00:00:00';

UPDATE recipe_steps SET created_at = NOW(), updated_at = NOW()
WHERE created_at IS NULL OR created_at <= '0000-00-00 00:00:00'
   OR updated_at IS NULL OR updated_at <= '0000-00-00 00:00:00';
