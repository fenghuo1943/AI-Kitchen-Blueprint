<?php
namespace App\Repositories;

use App\Core\Database;

class FavoriteRepository
{
    private $db;

    public function __construct()
    {
        $this->db = Database::getInstance();
    }

    public function getByUser($userId, int $offset = 0, int $limit = 30)
    {
        return $this->db->query(
            "SELECT f.id, f.recipe_id, f.created_at, r.title, r.cover
             FROM user_favorites f
             JOIN user_recipes r ON f.recipe_id = r.id
             WHERE f.user_id = ?
             ORDER BY f.created_at DESC
             LIMIT $offset, $limit",

            [$userId]
        );
    }
    public function countByUser($userId)
    {
        $result = $this->db->query(
            "SELECT COUNT(*) as total FROM user_favorites WHERE user_id = ?",
            [$userId]
        );
        return $result[0]['total'] ?? 0;
    }
    public function isFavorite($userId, $recipeId)
    {
        $result = $this->db->query(
            "SELECT id FROM user_favorites
             WHERE user_id = ? AND recipe_id = ?",
            [$userId, $recipeId]
        );
        return !empty($result);
    }

    // 利用 UNIQUE 约束防止重复
    public function insertIgnore($userId, $recipeId)
    {
        $this->db->execute(
            "INSERT IGNORE INTO user_favorites (user_id, recipe_id)
             VALUES (?, ?)",
            [$userId, $recipeId]
        );
    }

    public function delete($userId, $recipeId)
    {
        $this->db->execute(
            "DELETE FROM user_favorites
             WHERE user_id = ? AND recipe_id = ?",
            [$userId, $recipeId]
        );
    }
}