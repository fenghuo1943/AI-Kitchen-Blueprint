<?php
namespace App\Repositories;

use App\Core\Database;

class HistoryRepository
{
    private $db;

    public function __construct()
    {
        $this->db = Database::getInstance();
    }

    public function getByUser($userId, int $offset = 0, int $limit = 30)
    {
        return $this->db->query(
            "SELECT h.id, h.recipe_id, h.viewed_at, r.title, r.cover
             FROM user_history h
             JOIN user_recipes r ON h.recipe_id = r.id
             WHERE h.user_id = ?
             ORDER BY h.viewed_at DESC
             LIMIT $offset, $limit",
            [$userId]
        );
    }

    public function countByUser($userId)
    {
        $result = $this->db->query(
            "SELECT COUNT(*) as total FROM user_history WHERE user_id = ?",
            [$userId]
        );
        return $result[0]['total'] ?? 0;
    }

    // 利用 UNIQUE(user_id, recipe_id)
    public function upsert($userId, $recipeId)
    {
        $this->db->execute(
            "INSERT INTO user_history (user_id, recipe_id, viewed_at)
             VALUES (?, ?, NOW())
             ON DUPLICATE KEY UPDATE viewed_at = NOW()",
            [$userId, $recipeId]
        );
    }

    public function deleteByUser($userId)
    {
        $this->db->execute(
            "DELETE FROM user_history WHERE user_id = ?",
            [$userId]
        );
    }
}