-- create_schema.sql
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;;
SET FOREIGN_KEY_CHECKS = 0;
-- ======================================
-- users 表
-- ======================================
CREATE TABLE IF NOT EXISTS users (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ======================================
-- 菜谱主表
-- ======================================
CREATE TABLE IF NOT EXISTS user_recipes (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNSIGNED NOT NULL,
    title VARCHAR(200) NOT NULL,
    pinyin VARCHAR(255) NOT NULL,
    cover VARCHAR(255) DEFAULT NULL,
    description TEXT,
    cook_time INT DEFAULT NULL COMMENT '分钟',

    -- 冗余统计字段（高性能）
    view_count INT UNSIGNED DEFAULT 0,
    favorite_count INT UNSIGNED DEFAULT 0,

    is_deleted TINYINT(1) AS (deleted_at IS NOT NULL) STORED,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at DATETIME NULL,

    INDEX idx_user_not_deleted (user_id, is_deleted, created_at),
    INDEX idx_created (created_at),
    INDEX idx_not_deleted_created (is_deleted, created_at),
    UNIQUE KEY uk_user_title_not_deleted (user_id, title),
    FULLTEXT KEY ft_title_description (title, description),
    INDEX idx_pinyin (pinyin),
    INDEX idx_title (title),

    CONSTRAINT fk_user_recipes_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ======================================
-- 食材分类相关表
-- ======================================
CREATE TABLE IF NOT EXISTS user_ing_categories (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS user_ingredients (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    pinyin VARCHAR(255) NOT NULL,
    category_id INT UNSIGNED DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    INDEX(category_id),
    INDEX(name),
    INDEX(pinyin),

    CONSTRAINT fk_user_ingredients_category
        FOREIGN KEY (category_id)
        REFERENCES user_ing_categories(id)
        ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS user_recipe_ingredients (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    recipe_id INT UNSIGNED NOT NULL,
    ingredient_id INT UNSIGNED NOT NULL,
    quantity VARCHAR(100) DEFAULT NULL,

    UNIQUE KEY unique_recipe_ingredient (recipe_id, ingredient_id),
    INDEX(ingredient_id),

    CONSTRAINT fk_recipe_ingredients_recipe
        FOREIGN KEY (recipe_id)
        REFERENCES user_recipes(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_recipe_ingredients_ingredient
        FOREIGN KEY (ingredient_id)
        REFERENCES user_ingredients(id)
        ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ======================================
-- 步骤表
-- ======================================
CREATE TABLE IF NOT EXISTS user_steps (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    recipe_id INT UNSIGNED NOT NULL,
    step_order INT NOT NULL,
    content TEXT NOT NULL,
    image VARCHAR(255) DEFAULT NULL,

    UNIQUE KEY unique_step_order (recipe_id, step_order),
    INDEX(recipe_id),

    CONSTRAINT fk_user_steps_recipe
        FOREIGN KEY (recipe_id)
        REFERENCES user_recipes(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ======================================
-- 收藏表
-- ======================================
CREATE TABLE IF NOT EXISTS user_favorites (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNSIGNED NOT NULL,
    recipe_id INT UNSIGNED NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY unique_favorite (user_id, recipe_id),
    INDEX(recipe_id),

    CONSTRAINT fk_user_favorites_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_user_favorites_recipe
        FOREIGN KEY (recipe_id)
        REFERENCES user_recipes(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ======================================
-- 浏览历史
-- ======================================
CREATE TABLE IF NOT EXISTS user_history (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNSIGNED NOT NULL,
    recipe_id INT UNSIGNED NOT NULL,
    viewed_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY (user_id, recipe_id),
    INDEX(recipe_id),
    INDEX idx_user_viewed (user_id, viewed_at),

    CONSTRAINT fk_user_history_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_user_history_recipe
        FOREIGN KEY (recipe_id)
        REFERENCES user_recipes(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ======================================
-- 用户分类、菜谱分类、调料相关表
-- ======================================
CREATE TABLE IF NOT EXISTS user_categories (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    parent_id INT UNSIGNED DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX(parent_id),

    CONSTRAINT fk_user_categories_parent
        FOREIGN KEY (parent_id)
        REFERENCES user_categories(id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS user_recipe_categories (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    recipe_id INT UNSIGNED NOT NULL,
    category_id INT UNSIGNED NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY unique_mapping (recipe_id, category_id),
    INDEX(recipe_id),
    INDEX(category_id),

    CONSTRAINT fk_recipe_categories_recipe
        FOREIGN KEY (recipe_id)
        REFERENCES user_recipes(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_recipe_categories_category
        FOREIGN KEY (category_id)
        REFERENCES user_categories(id)
        ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS user_seasoning_categories (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS user_seasonings (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    pinyin VARCHAR(255) NOT NULL,
    category_id INT UNSIGNED DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    INDEX(category_id),
    INDEX(name),
    INDEX(pinyin),

    CONSTRAINT fk_user_seasonings_category
        FOREIGN KEY (category_id)
        REFERENCES user_seasoning_categories(id)
        ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS user_recipe_seasonings (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    recipe_id INT UNSIGNED NOT NULL,
    seasoning_id INT UNSIGNED NOT NULL,
    quantity VARCHAR(100) DEFAULT NULL,

    UNIQUE KEY unique_recipe_seasoning (recipe_id, seasoning_id),
    INDEX(seasoning_id),
    INDEX(recipe_id),

    CONSTRAINT fk_recipe_seasonings_recipe
        FOREIGN KEY (recipe_id)
        REFERENCES user_recipes(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_recipe_seasonings_seasoning
        FOREIGN KEY (seasoning_id)
        REFERENCES user_seasonings(id)
        ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ======================================
-- 用户今日菜谱表
-- ======================================
CREATE TABLE IF NOT EXISTS user_daily_recipes (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNSIGNED NOT NULL COMMENT '用户ID',
    recipe_id INT UNSIGNED NOT NULL COMMENT '菜谱ID',
    target_date DATE NOT NULL COMMENT '指定日期',

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY unique_user_recipe_date (user_id, recipe_id, target_date),
    INDEX idx_user_date (user_id, target_date),
    INDEX idx_recipe_id (recipe_id),
    INDEX idx_target_date (target_date),

    CONSTRAINT fk_daily_recipe_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_daily_recipe_recipe
        FOREIGN KEY (recipe_id)
        REFERENCES user_recipes(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ======================================
-- 默认分类
-- ======================================
INSERT IGNORE INTO user_categories (id, name) VALUES (1, '默认');
INSERT IGNORE INTO user_ing_categories (id, name) VALUES (1, '默认');
INSERT IGNORE INTO user_seasoning_categories (id, name) VALUES (1, '默认');

SET FOREIGN_KEY_CHECKS = 1;

-- 禁止删除默认分类
DROP TRIGGER IF EXISTS prevent_delete_default_category;
DROP TRIGGER IF EXISTS prevent_update_default_category;

DELIMITER $$

CREATE TRIGGER prevent_delete_default_category
BEFORE DELETE ON user_categories
FOR EACH ROW
BEGIN
    IF OLD.id = 1 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = '默认分类不可删除';
    END IF;
END$$

CREATE TRIGGER prevent_update_default_category
BEFORE UPDATE ON user_categories
FOR EACH ROW
BEGIN
    IF OLD.id = 1 AND NEW.id <> 1 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = '默认分类ID不可修改';
    END IF;
END$$

DELIMITER ;

DROP TRIGGER IF EXISTS prevent_delete_default_ing_category;
DROP TRIGGER IF EXISTS prevent_update_default_ing_category;

DELIMITER $$

CREATE TRIGGER prevent_delete_default_ing_category
BEFORE DELETE ON user_ing_categories
FOR EACH ROW
BEGIN
    IF OLD.id = 1 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = '默认食材分类不可删除';
    END IF;
END$$

CREATE TRIGGER prevent_update_default_ing_category
BEFORE UPDATE ON user_ing_categories
FOR EACH ROW
BEGIN
    IF OLD.id = 1 AND NEW.id <> 1 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = '默认食材分类ID不可修改';
    END IF;
END$$

DELIMITER ;
DROP TRIGGER IF EXISTS prevent_delete_default_seasoning_category;
DROP TRIGGER IF EXISTS prevent_update_default_seasoning_category;

DELIMITER $$

CREATE TRIGGER prevent_delete_default_seasoning_category
BEFORE DELETE ON user_seasoning_categories
FOR EACH ROW
BEGIN
    IF OLD.id = 1 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = '默认调料分类不可删除';
    END IF;
END$$

CREATE TRIGGER prevent_update_default_seasoning_category
BEFORE UPDATE ON user_seasoning_categories
FOR EACH ROW
BEGIN
    IF OLD.id = 1 AND NEW.id <> 1 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = '默认调料分类ID不可修改';
    END IF;
END$$

DELIMITER ;

-- 定期清理已删除的菜谱（例如，30天前的记录）
CREATE EVENT IF NOT EXISTS ev_cleanup_deleted_recipes
ON SCHEDULE EVERY 1 DAY
STARTS CURRENT_TIMESTAMP + INTERVAL 1 DAY
DO
DELETE FROM user_recipes
WHERE deleted_at IS NOT NULL
  AND deleted_at < NOW() - INTERVAL 30 DAY;