<?php

namespace App\Repositories;

use App\Core\Database;

class DiscoverRepository {
    private $db;
    public function __construct() {
        $this->db = Database::getInstance();
    }
    /**
     * 今日推荐
     */
    public function findTodayRecommend($userId, int $limit = 6) {
        if ($limit < 2) {
            $limit = 2;
        }
        if ($limit >= 4) {
            $limit2 = 2;
        } else {
            $limit2 = 1;
        }
        $limit1 = $limit - $limit2;
        $sqlScore = "
            SELECT 
                r.id,
                r.user_id,
                r.title,
                r.description,
                r.cook_time,
                r.created_at,
                r.deleted_at,
                IFNULL(dc.cooked_count,0) AS cooked_count,
                IF(fav.recipe_id IS NULL,0,1) AS is_favorited,
                IF(today.recipe_id IS NULL,0,1) AS is_in_today_menu,
                (IFNULL(dc.cooked_count,0)*2 + IF(fav.recipe_id IS NULL,0,3) + RAND(CURDATE()))+0 AS score
            FROM user_recipes r
            /* 做过次数 */
            LEFT JOIN (
                SELECT recipe_id, COUNT(*) AS cooked_count
                FROM user_daily_recipes
                WHERE user_id = ?
                GROUP BY recipe_id
            ) dc ON r.id = dc.recipe_id
                /* 收藏 */
            LEFT JOIN user_favorites fav
                ON fav.recipe_id = r.id
                AND fav.user_id = ?
            /* 今日菜单 */
            LEFT JOIN user_daily_recipes today
                ON today.recipe_id = r.id
                AND today.user_id = ?
                AND today.target_date = CURDATE()
            WHERE r.is_deleted = 0
            ORDER BY score DESC
            LIMIT $limit1
        ";
        $top4 = $this->db->query($sqlScore, [$userId, $userId, $userId]);
        $excludedIds = array_column($top4, 'id');
        $placeholders = implode(',', array_fill(0, count($excludedIds), '?'));
        $sqlRand = "
            SELECT 
            r.id,
                r.user_id,
                r.title,
                r.description,
                r.cook_time,
                r.created_at,
                r.deleted_at,
                IFNULL(dc.cooked_count,0) AS cooked_count,
                IF(fav.recipe_id IS NULL,0,1) AS is_favorited,
                IF(today.recipe_id IS NULL,0,1) AS is_in_today_menu
            FROM user_recipes r
            /* 做过次数 */
            LEFT JOIN (
                SELECT recipe_id, COUNT(*) AS cooked_count
                FROM user_daily_recipes
                WHERE user_id = ?
                GROUP BY recipe_id
            ) dc ON r.id = dc.recipe_id

            /* 收藏 */
            LEFT JOIN user_favorites fav
                ON fav.recipe_id = r.id
                AND fav.user_id = ?

            /* 今日菜单 */
            LEFT JOIN user_daily_recipes today
                ON today.recipe_id = r.id
                AND today.user_id = ?
                AND today.target_date = CURDATE()
            WHERE is_deleted = 0
            " . (!empty($excludedIds) ? "AND r.id NOT IN ($placeholders)" : "") . "
            ORDER BY RAND()
            LIMIT $limit2";

        $randParams = array_merge([$userId, $userId, $userId],$excludedIds);
        $last2 = $this->db->query($sqlRand, $randParams);
        return array_merge($top4, $last2);


        $sql = "
            SELECT 
                r.id,
                r.user_id,
                r.title,
                r.description,
                r.cook_time,
                r.created_at,
                r.deleted_at,
                IFNULL(dc.cooked_count,0) AS cooked_count,
                IF(fav.recipe_id IS NULL,0,1) AS is_favorited,
                IF(today.recipe_id IS NULL,0,1) AS is_in_today_menu,
                (IFNULL(dc.cooked_count,0)*2 + IF(fav.recipe_id IS NULL,0,3) + RAND(CURDATE()))+0 AS score
            FROM user_recipes r
            /* 做过次数 */
            LEFT JOIN (
                SELECT recipe_id, COUNT(*) AS cooked_count
                FROM user_daily_recipes
                WHERE user_id = ?
                GROUP BY recipe_id
            ) dc ON r.id = dc.recipe_id
             /* 收藏 */
            LEFT JOIN user_favorites fav
                ON fav.recipe_id = r.id
                AND fav.user_id = ?
            /* 今日菜单 */
            LEFT JOIN user_daily_recipes today
                ON today.recipe_id = r.id
                AND today.user_id = ?
                AND today.target_date = CURDATE()
            WHERE is_deleted = 0
            ORDER BY score DESC
            LIMIT $limit
        ";

        return $this->db->query($sql, [$userId, $userId, $userId]);
    }
    /**
     * 热门菜谱
     */
    public function findHotRecipes($userId, int $limit = 6) {
        $sql = "
            SELECT 
                r.id,
                r.user_id,
                r.title,
                r.description,
                r.cook_time,
                r.created_at,
                r.deleted_at,
                IFNULL(dc.cooked_count,0) AS cooked_count,
                IF(fav.recipe_id IS NULL,0,1) AS is_favorited,
                IF(today.recipe_id IS NULL,0,1) AS is_in_today_menu,
                (view_count*3 + IFNULL(dc.cooked_count,0)*2 + IF(fav.recipe_id IS NULL,0,3) + RAND()*0.1) AS score
            FROM user_recipes r
            /* 做过次数 */
            LEFT JOIN (
                SELECT recipe_id, COUNT(*) AS cooked_count
                FROM user_daily_recipes
                WHERE user_id = ?
                GROUP BY recipe_id
            ) dc ON r.id = dc.recipe_id
             /* 收藏 */
            LEFT JOIN user_favorites fav
                ON fav.recipe_id = r.id
                AND fav.user_id = ?
            /* 今日菜单 */
            LEFT JOIN user_daily_recipes today
                ON today.recipe_id = r.id
                AND today.user_id = ?
                AND today.target_date = CURDATE()
            WHERE is_deleted = 0
            ORDER BY score DESC
            LIMIT $limit
        ";

        return $this->db->query($sql, [$userId, $userId, $userId]);
    }
    /**
     * 最新菜谱
     */
    public function findNewRecipes($userId, int $limit = 6) {
        $sql = "
            SELECT 
                r.id,
                r.user_id,
                r.title,
                r.description,
                r.cook_time,
                r.created_at,
                r.deleted_at,
                IFNULL(dc.cooked_count,0) AS cooked_count,
                IF(fav.recipe_id IS NULL,0,1) AS is_favorited,
                IF(today.recipe_id IS NULL,0,1) AS is_in_today_menu
            FROM user_recipes r
            /* 做过次数 */
            LEFT JOIN (
                SELECT recipe_id, COUNT(*) AS cooked_count
                FROM user_daily_recipes
                WHERE user_id = ?
                GROUP BY recipe_id
            ) dc ON r.id = dc.recipe_id

            /* 收藏 */
            LEFT JOIN user_favorites fav
                ON fav.recipe_id = r.id
                AND fav.user_id = ?

            /* 今日菜单 */
            LEFT JOIN user_daily_recipes today
                ON today.recipe_id = r.id
                AND today.user_id = ?
                AND today.target_date = CURDATE()
            WHERE is_deleted = 0
            ORDER BY created_at DESC
            LIMIT $limit
        ";

        return $this->db->query($sql, [$userId, $userId, $userId]);
    }
    /**
     * 随机菜谱
     */
    public function findRandomRecipes($userId, int $limit = 6) {
        $sql = "
            SELECT 
                r.id,
                r.user_id,
                r.title,
                r.description,
                r.cook_time,
                r.created_at,
                r.deleted_at,
                IFNULL(dc.cooked_count,0) AS cooked_count,
                IF(fav.recipe_id IS NULL,0,1) AS is_favorited,
                IF(today.recipe_id IS NULL,0,1) AS is_in_today_menu
            FROM user_recipes r
            /* 做过次数 */
            LEFT JOIN (
                SELECT recipe_id, COUNT(*) AS cooked_count
                FROM user_daily_recipes
                WHERE user_id = ?
                GROUP BY recipe_id
            ) dc ON r.id = dc.recipe_id

            /* 收藏 */
            LEFT JOIN user_favorites fav
                ON fav.recipe_id = r.id
                AND fav.user_id = ?

            /* 今日菜单 */
            LEFT JOIN user_daily_recipes today
                ON today.recipe_id = r.id
                AND today.user_id = ?
                AND today.target_date = CURDATE()
            WHERE is_deleted = 0
            ORDER BY RAND()
            LIMIT $limit
        ";

        return $this->db->query($sql, [$userId, $userId, $userId]);
    }
}
