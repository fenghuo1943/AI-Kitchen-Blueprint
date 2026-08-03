-- ============================================================
-- 002_add_cook_features.sql
-- 参考 cook 项目移植：分类体系 / 调料 / 收藏 / 浏览历史 / 每日菜单
-- 目标数据库：MariaDB（生产库），应用层 create_all 只建新表不改旧表，
-- 因此本脚本需在已有数据库上手动执行一次。
-- 执行：mysql -u cook -p -h 192.168.31.146 -P 3307 cook < 002_add_cook_features.sql
-- ============================================================

SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;
SET FOREIGN_KEY_CHECKS = 0;

-- ---------- 旧表补字段 ----------
ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS pinyin VARCHAR(255) NULL AFTER canonical_name;
ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS category_id VARCHAR(36) NULL AFTER category;
ALTER TABLE recipes ADD COLUMN IF NOT EXISTS pinyin VARCHAR(255) NULL AFTER title;
ALTER TABLE recipes ADD COLUMN IF NOT EXISTS cover VARCHAR(500) NULL AFTER summary;

-- ---------- 分类 / 调料 / 关联表 ----------
CREATE TABLE IF NOT EXISTS recipe_categories (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    parent_id VARCHAR(36) NULL,
    sort_order INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at DATETIME NULL,
    UNIQUE KEY uk_recipe_category_name (name),
    CONSTRAINT fk_recipe_categories_parent FOREIGN KEY (parent_id) REFERENCES recipe_categories(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ingredient_categories (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at DATETIME NULL,
    UNIQUE KEY uk_ingredient_category_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS seasoning_categories (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at DATETIME NULL,
    UNIQUE KEY uk_seasoning_category_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS seasonings (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    canonical_name VARCHAR(100) NOT NULL,
    pinyin VARCHAR(255) NULL,
    category_id VARCHAR(36) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at DATETIME NULL,
    UNIQUE KEY uk_seasoning_name (canonical_name),
    CONSTRAINT fk_seasonings_category FOREIGN KEY (category_id) REFERENCES seasoning_categories(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS recipe_seasonings (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    recipe_id VARCHAR(36) NOT NULL,
    seasoning_id VARCHAR(36) NOT NULL,
    quantity VARCHAR(50) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at DATETIME NULL,
    UNIQUE KEY uk_recipe_seasoning (recipe_id, seasoning_id),
    CONSTRAINT fk_recipe_seasonings_recipe FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
    CONSTRAINT fk_recipe_seasonings_seasoning FOREIGN KEY (seasoning_id) REFERENCES seasonings(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS recipe_category_links (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    recipe_id VARCHAR(36) NOT NULL,
    category_id VARCHAR(36) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at DATETIME NULL,
    UNIQUE KEY uk_recipe_category (recipe_id, category_id),
    CONSTRAINT fk_recipe_category_links_recipe FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
    CONSTRAINT fk_recipe_category_links_category FOREIGN KEY (category_id) REFERENCES recipe_categories(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------- 用户行为表 ----------
CREATE TABLE IF NOT EXISTS favorites (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    household_id VARCHAR(36) NOT NULL,
    recipe_id VARCHAR(36) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at DATETIME NULL,
    UNIQUE KEY uk_favorite_household_recipe (household_id, recipe_id),
    KEY idx_favorites_household_created (household_id, created_at),
    CONSTRAINT fk_favorites_household FOREIGN KEY (household_id) REFERENCES households(id) ON DELETE CASCADE,
    CONSTRAINT fk_favorites_recipe FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS recipe_history (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    household_id VARCHAR(36) NOT NULL,
    recipe_id VARCHAR(36) NOT NULL,
    viewed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at DATETIME NULL,
    UNIQUE KEY uk_history_household_recipe (household_id, recipe_id),
    KEY idx_history_household_viewed (household_id, viewed_at),
    CONSTRAINT fk_history_household FOREIGN KEY (household_id) REFERENCES households(id) ON DELETE CASCADE,
    CONSTRAINT fk_history_recipe FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS meal_plans (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    household_id VARCHAR(36) NOT NULL,
    recipe_id VARCHAR(36) NOT NULL,
    target_date DATE NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at DATETIME NULL,
    UNIQUE KEY uk_meal_plan (household_id, recipe_id, target_date),
    KEY idx_meal_plan_household_date (household_id, target_date),
    CONSTRAINT fk_meal_plans_household FOREIGN KEY (household_id) REFERENCES households(id) ON DELETE CASCADE,
    CONSTRAINT fk_meal_plans_recipe FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------- 默认分类种子 ----------
-- 注意：显式写入 created_at/updated_at，避免表无服务端默认值时插入零值日期（'0000-00-00 00:00:00'）
INSERT IGNORE INTO ingredient_categories (id, name, created_at, updated_at) SELECT '1', '默认', NOW(), NOW();
INSERT IGNORE INTO seasoning_categories (id, name, created_at, updated_at) SELECT '1', '默认', NOW(), NOW();
INSERT IGNORE INTO recipe_categories (id, name, created_at, updated_at) SELECT '1', '默认', NOW(), NOW();

-- ---------- 回填：食材字符串分类 → 食材分类表 ----------
-- 将 ingredients.category 的旧字符串值插入 ingredient_categories（如蔬菜/肉类/主食/蛋类/豆制品/水产/调料）
INSERT IGNORE INTO ingredient_categories (id, name, created_at, updated_at)
SELECT UUID(), category, NOW(), NOW() FROM ingredients WHERE category IS NOT NULL AND category <> '' AND deleted_at IS NULL;
-- 回填 category_id（按名称精确匹配）
UPDATE ingredients i
JOIN ingredient_categories c ON c.name = i.category AND c.deleted_at IS NULL
SET i.category_id = c.id
WHERE i.category_id IS NULL AND i.category IS NOT NULL AND i.category <> '';

SET FOREIGN_KEY_CHECKS = 1;
