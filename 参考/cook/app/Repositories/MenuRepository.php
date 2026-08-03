<?php

namespace App\Repositories;

use App\Core\Database;

class MenuRepository {
    private Database $db;

    public function __construct() {
        $this->db = Database::getInstance();
    }

    /**
     * 添加菜谱到某天
     */
    public function addRecipe(int $userId, int $recipeId, string $date): void {
        $this->db->execute(
            "INSERT IGNORE INTO user_daily_recipes 
             (user_id, recipe_id, target_date) 
             VALUES (?, ?, ?)",
            [$userId, $recipeId, $date]
        );
    }

    /**
     * 删除某天的某个菜谱
     */
    public function removeRecipe(int $userId, int $recipeId, string $date): void {
        $this->db->execute(
            "DELETE FROM user_daily_recipes
             WHERE user_id = ?
               AND recipe_id = ?
               AND target_date = ?",
            [$userId, $recipeId, $date]
        );
    }

    /**
     * 查询某天的菜单
     */
    public function getByDate(int $userId, string $date): array {
        return $this->db->query(
            "SELECT r.id, r.title, r.cover, r.cook_time
             FROM user_daily_recipes d
             JOIN user_recipes r ON r.id = d.recipe_id
             WHERE d.user_id = ?
               AND d.target_date = ?
             ORDER BY d.created_at ASC",
            [$userId, $date]
        );
    }
    /**
     * 查询某天的菜谱中的所有食材
     */
    public function getIngredientsByDate(int $userId, string $date): array {
        return $this->db->query(
            "SELECT i.id, i.name
         FROM user_daily_recipes d
         JOIN user_recipes r ON r.id = d.recipe_id
         JOIN user_recipe_ingredients ri ON ri.recipe_id = r.id
         JOIN user_ingredients i ON i.id = ri.ingredient_id
         WHERE d.user_id = ?
           AND d.target_date = ?
         ORDER BY i.pinyin ASC",
            [$userId, $date]
        );
    }
    /**
     * 查询某天的菜谱中的所有调料
     */
    public function getSeasoningsByDate(int $userId, string $date): array {
        return $this->db->query(
            "SELECT i.id, i.name
         FROM user_daily_recipes d
         JOIN user_recipes r ON r.id = d.recipe_id
         JOIN user_recipe_seasonings ri ON ri.recipe_id = r.id
         JOIN user_seasonings i ON i.id = ri.seasoning_id
         WHERE d.user_id = ?
           AND d.target_date = ?
         ORDER BY i.pinyin ASC",
            [$userId, $date]
        );
    }

    /**
     * 查询当天是否已存在该菜谱
     */
    public function existsInDate(int $userId, int $recipeId, ?string $date = null): bool {
        $date = $date ?: date('Y-m-d');
        $row = $this->db->queryOne(
            "SELECT id FROM user_daily_recipes
             WHERE user_id = ?
               AND recipe_id = ?
               AND target_date = ?
             LIMIT 1",
            [$userId, $recipeId, $date]
        );

        return !empty($row);
    }
    /**
     * 瀑布流查询（按天分组前的原始数据）
     */
    public function getAllByUser(int $userId): array {
        return $this->db->query(
            "SELECT d.target_date,
                    r.id,
                    r.title,
                    r.cover,
                    r.cook_time
             FROM user_daily_recipes d
             JOIN user_recipes r ON r.id = d.recipe_id
             WHERE d.user_id = ?
             ORDER BY d.target_date DESC, d.created_at ASC",
            [$userId]
        );
    }
    public function getByUserWithPage(int $userId, int $page, int $pageSize): array {
        $offset = ($page - 1) * $pageSize;
        // 1️⃣ 先查分页日期
        $dates = $this->db->query(
            "SELECT DISTINCT target_date
         FROM user_daily_recipes
         WHERE user_id = ?
         ORDER BY target_date DESC
         LIMIT $offset, $pageSize",
            [$userId]
        );
        if (!$dates) return [
            'list' => [],
            'totalPage' => 0
        ];
        $dateArr = array_column($dates, 'target_date');
        if (empty($dateArr)) {
            return [
                'list' => [],
                'totalPage' => 0
            ];
        }
        // 2️⃣ 再查这些日期下的菜谱
        $in = implode(',', array_fill(0, count($dateArr), '?'));
        $rows = $this->db->query(
            "SELECT d.target_date,
                r.id,
                r.title,
                r.cover,
                r.cook_time
         FROM user_daily_recipes d
         JOIN user_recipes r ON r.id = d.recipe_id
         WHERE d.user_id = ?
           AND d.target_date IN ($in)
         ORDER BY d.target_date DESC, d.created_at ASC",
            array_merge([$userId], $dateArr)
        );
        return [
            'list' => $rows,
            'totalPage' => ceil($this->getDateCount($userId) / $pageSize)
        ];
        if (empty($rows) || !is_array($rows)) {
            return [
                'list' => [],
                'totalPage' => ceil($this->getDateCount($userId) / $pageSize)
            ];
        }
        // 3️⃣ 按天分组
        $grouped = [];
        foreach ($rows as $row) {
            $date = $row['target_date'];
            if (!isset($grouped[$date])) {
                $grouped[$date] = [
                    'date' => $date,
                    'recipes' => []
                ];
            }
            $grouped[$date]['recipes'][] = $row;
        }
        return [
            'list' => array_values($grouped),
            'totalPage' => ceil($this->getDateCount($userId) / $pageSize)
        ];
    }

    /**
     * 查询某天是否已存在该菜谱
     */
    public function exists(int $userId, int $recipeId, string $date): bool {
        $row = $this->db->queryOne(
            "SELECT id FROM user_daily_recipes
             WHERE user_id = ?
               AND recipe_id = ?
               AND target_date = ?
             LIMIT 1",
            [$userId, $recipeId, $date]
        );

        return !empty($row);
    }
    /**
     * 获取某月有菜单的日期
     */
    public function getDatesByMonth(int $userId, string $month): array {
        return $this->db->query(
            "SELECT DISTINCT target_date
         FROM user_daily_recipes
         WHERE user_id = ?
           AND DATE_FORMAT(target_date, '%Y-%m') = ?
         ORDER BY target_date ASC",
            [$userId, $month]
        );
    }
    /**
     * 获取有菜单的天数
     */
    private function getDateCount(int $userId): int {
        $res = $this->db->query(
            "SELECT COUNT(DISTINCT target_date) as total
         FROM user_daily_recipes
         WHERE user_id = ?",
            [$userId]
        );
        return $res[0]['total'] ?? 0;
    }
}
