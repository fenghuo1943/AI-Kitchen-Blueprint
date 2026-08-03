<?php
/**
 * 数据库初始化脚本
 * 用于创建或升级菜谱数据库表
 */

require dirname(__FILE__) . '/../zb_system/function/c_system_base.php';
$zbp->Load();

/* if (!$zbp->user->ID || !$zbp->CheckPlugin('AdminCenter')) {
    die("需要管理员权限");
} */

$errors = array();
$success = array();

// 1. 创建用户食材表（带默认分类）
$sql = "CREATE TABLE IF NOT EXISTS user_ingredients (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    category_id INT UNSIGNED DEFAULT 1 COMMENT '默认食材分类ID',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX(category_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4";

if (!$zbp->db->Query($sql)) {
    $errors[] = "创建 user_ingredients 表失败";
} else {
    $success[] = "user_ingredients 表 OK";
}

// 2. 创建菜谱表（带默认分类）
$sql = "CREATE TABLE IF NOT EXISTS user_recipes (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNSIGNED NOT NULL,
    title VARCHAR(200) NOT NULL,
    cover VARCHAR(255) DEFAULT NULL,
    description TEXT,
    cook_time INT DEFAULT NULL COMMENT '分钟',
    category_id INT UNSIGNED DEFAULT 1 COMMENT '默认分类ID',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX(user_id),
    INDEX(title),
    INDEX(category_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4";

if (!$zbp->db->Query($sql)) {
    $errors[] = "创建 user_recipes 表失败";
} else {
    $success[] = "user_recipes 表 OK";
}

// 3. 创建菜谱-食材关系表
$sql = "CREATE TABLE IF NOT EXISTS user_recipe_ingredients (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    recipe_id INT UNSIGNED NOT NULL,
    ingredient_id INT UNSIGNED NOT NULL,
    amount VARCHAR(100) DEFAULT NULL,
    INDEX(recipe_id),
    INDEX(ingredient_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4";

if (!$zbp->db->Query($sql)) {
    $errors[] = "创建 user_recipe_ingredients 表失败";
} else {
    $success[] = "user_recipe_ingredients 表 OK";
}

// 4. 创建步骤表
$sql = "CREATE TABLE IF NOT EXISTS user_steps (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    recipe_id INT UNSIGNED NOT NULL,
    step_order INT NOT NULL,
    content TEXT NOT NULL,
    image VARCHAR(255) DEFAULT NULL,
    INDEX(recipe_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4";

if (!$zbp->db->Query($sql)) {
    $errors[] = "创建 user_steps 表失败";
} else {
    $success[] = "user_steps 表 OK";
}

// 5. 创建收藏表
$sql = "CREATE TABLE IF NOT EXISTS user_favorites (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNSIGNED NOT NULL,
    recipe_id INT UNSIGNED NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_favorite (user_id, recipe_id),
    INDEX(recipe_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4";

if (!$zbp->db->Query($sql)) {
    $errors[] = "创建 user_favorites 表失败";
} else {
    $success[] = "user_favorites 表 OK";
}

// 6. 创建分类表
$sql = "CREATE TABLE IF NOT EXISTS user_categories (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    parent_id INT UNSIGNED DEFAULT NULL COMMENT '父分类，可空',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX(parent_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4";

if (!$zbp->db->Query($sql)) {
    $errors[] = "创建 user_categories 表失败";
} else {
    $success[] = "user_categories 表 OK";
}

// 7. 创建菜谱-分类关系表
$sql = "CREATE TABLE IF NOT EXISTS user_recipe_categories (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    recipe_id INT UNSIGNED NOT NULL,
    category_id INT UNSIGNED NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX (recipe_id),
    INDEX (category_id),
    UNIQUE KEY unique_mapping (recipe_id, category_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4";

if (!$zbp->db->Query($sql)) {
    $errors[] = "创建 user_recipe_categories 表失败";
} else {
    $success[] = "user_recipe_categories 表 OK";
}

// 8. 创建食材分类表
$sql = "CREATE TABLE IF NOT EXISTS user_ing_categories (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4";

if (!$zbp->db->Query($sql)) {
    $errors[] = "创建 user_ing_categories 表失败";
} else {
    $success[] = "user_ing_categories 表 OK";
}

// 9. 确保默认分类存在（ID为1）
$defaultCatSQL = "INSERT IGNORE INTO user_categories (id, name) VALUES (1, '默认')";
if ($zbp->db->Query($defaultCatSQL)) {
    $success[] = "已确保默认分类存在: ID=1, 名称=默认";
} else {
    $errors[] = "确保默认分类存在失败";
}

// 10. 确保默认食材分类存在（ID为1）
$defaultIngCatSQL = "INSERT IGNORE INTO user_ing_categories (id, name) VALUES (1, '默认')";
if ($zbp->db->Query($defaultIngCatSQL)) {
    $success[] = "已确保默认食材分类存在: ID=1, 名称=默认";
} else {
    $errors[] = "确保默认食材分类存在失败";
}

// 11. 检查和添加食材分类字段（如果表已存在但缺少该字段）
$sql = "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'user_ingredients' AND COLUMN_NAME = 'category_id'";
$rs = $zbp->db->Query($sql);
if (!$rs || empty($rs)) {
    // 列不存在，需要添加
    $sql = "ALTER TABLE user_ingredients ADD COLUMN category_id INT UNSIGNED DEFAULT 1 COMMENT '默认食材分类ID'";
    if (!$zbp->db->Query($sql)) {
        $errors[] = "添加 user_ingredients.category_id 列失败";
    } else {
        $success[] = "已添加 user_ingredients.category_id 列";
    }
    
    // 添加索引
    $sql = "ALTER TABLE user_ingredients ADD INDEX category_id (category_id)";
    if (!$zbp->db->Query($sql)) {
        $errors[] = "添加索引失败";
    } else {
        $success[] = "已添加索引";
    }
    
    // 添加外键约束
    $sql = "ALTER TABLE user_ingredients ADD CONSTRAINT fk_ing_category FOREIGN KEY (category_id) REFERENCES user_ing_categories(id) ON DELETE SET NULL";
    if (!$zbp->db->Query($sql)) {
        $errors[] = "添加外键约束失败";
    } else {
        $success[] = "已添加外键约束";
    }
} else {
    $success[] = "user_ingredients.category_id 列已存在";
}

// 12. 检查和添加菜谱分类字段（如果表已存在但缺少该字段）
$sql = "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'user_recipes' AND COLUMN_NAME = 'category_id'";
$rs = $zbp->db->Query($sql);
if (!$rs || empty($rs)) {
    // 列不存在，需要添加
    $sql = "ALTER TABLE user_recipes ADD COLUMN category_id INT UNSIGNED DEFAULT 1 COMMENT '默认分类ID'";
    if (!$zbp->db->Query($sql)) {
        $errors[] = "添加 user_recipes.category_id 列失败";
    } else {
        $success[] = "已添加 user_recipes.category_id 列";
    }
    
    // 添加索引
    $sql = "ALTER TABLE user_recipes ADD INDEX category_id (category_id)";
    if (!$zbp->db->Query($sql)) {
        $errors[] = "添加索引失败";
    } else {
        $success[] = "已添加索引";
    }
    
    // 添加外键约束
    $sql = "ALTER TABLE user_recipes ADD CONSTRAINT fk_recipe_category FOREIGN KEY (category_id) REFERENCES user_categories(id) ON DELETE SET NULL";
    if (!$zbp->db->Query($sql)) {
        $errors[] = "添加外键约束失败";
    } else {
        $success[] = "已添加外键约束";
    }
} else {
    $success[] = "user_recipes.category_id 列已存在";
}

// 在所有表创建完成后，再添加外键约束
$foreignKeys = [
    "ALTER TABLE user_recipes ADD CONSTRAINT fk_recipe_category FOREIGN KEY (category_id) REFERENCES user_categories(id) ON DELETE SET NULL",
    "ALTER TABLE user_ingredients ADD CONSTRAINT fk_ing_category FOREIGN KEY (category_id) REFERENCES user_ing_categories(id) ON DELETE SET NULL",
    "ALTER TABLE user_recipe_ingredients ADD CONSTRAINT fk_recipe FOREIGN KEY (recipe_id) REFERENCES user_recipes(id) ON DELETE CASCADE",
    "ALTER TABLE user_recipe_ingredients ADD CONSTRAINT fk_ingredient FOREIGN KEY (ingredient_id) REFERENCES user_ingredients(id) ON DELETE CASCADE",
    "ALTER TABLE user_steps ADD CONSTRAINT fk_step_recipe FOREIGN KEY (recipe_id) REFERENCES user_recipes(id) ON DELETE CASCADE",
    "ALTER TABLE user_favorites ADD CONSTRAINT fk_favorite_user FOREIGN KEY (user_id) REFERENCES zbp_member(mem_ID) ON DELETE CASCADE",
    "ALTER TABLE user_favorites ADD CONSTRAINT fk_favorite_recipe FOREIGN KEY (recipe_id) REFERENCES user_recipes(id) ON DELETE CASCADE",
    "ALTER TABLE user_cooked_log ADD CONSTRAINT fk_cooked_user FOREIGN KEY (user_id) REFERENCES zbp_member(mem_ID) ON DELETE CASCADE",
    "ALTER TABLE user_cooked_log ADD CONSTRAINT fk_cooked_recipe FOREIGN KEY (recipe_id) REFERENCES user_recipes(id) ON DELETE CASCADE",
    "ALTER TABLE user_history ADD CONSTRAINT fk_history_user FOREIGN KEY (user_id) REFERENCES zbp_member(mem_ID) ON DELETE CASCADE",
    "ALTER TABLE user_history ADD CONSTRAINT fk_history_recipe FOREIGN KEY (recipe_id) REFERENCES user_recipes(id) ON DELETE CASCADE",
    "ALTER TABLE user_categories ADD CONSTRAINT fk_parent_category FOREIGN KEY (parent_id) REFERENCES user_categories(id) ON DELETE SET NULL",
    "ALTER TABLE user_recipe_categories ADD CONSTRAINT fk_rc_recipe FOREIGN KEY (recipe_id) REFERENCES user_recipes(id) ON DELETE CASCADE",
    "ALTER TABLE user_recipe_categories ADD CONSTRAINT fk_rc_category FOREIGN KEY (category_id) REFERENCES user_categories(id) ON DELETE CASCADE"
];

foreach ($foreignKeys as $fkSql) {
    if (!$zbp->db->Query($fkSql)) {
        $errors[] = "添加外键约束失败: " . $fkSql;
    } else {
        $success[] = "成功添加外键约束";
    }
}

// 输出结果
?>
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>数据库初始化</title>
    <style>
        body { font-family: Arial; padding: 20px; }
        .success { color: green; }
        .error { color: red; }
    </style>
</head>
<body>
    <h1>数据库初始化结果</h1>
    <?php if (!empty($success)): ?>
        <h2 class="success">成功:</h2>
        <ul>
            <?php foreach ($success as $msg): ?>
                <li><?php echo htmlspecialchars($msg); ?></li>
            <?php endforeach; ?>
        </ul>
    <?php endif; ?>
    
    <?php if (!empty($errors)): ?>
        <h2 class="error">错误:</h2>
        <ul>
            <?php foreach ($errors as $msg): ?>
                <li><?php echo htmlspecialchars($msg); ?></li>
            <?php endforeach; ?>
        </ul>
    <?php endif; ?>
    
    <?php if (empty($errors)): ?>
        <p><strong>✓ 数据库初始化完成! 默认分类ID已设置为1</strong></p>
    <?php endif; ?>
</body>
</html>