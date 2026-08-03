<?php

namespace App\Repositories;

use App\Core\Database;
use Overtrue\Pinyin\Pinyin;

class SeasoningRepository {
    private $db;
    private $pinyin;

    public function __construct() {
        $this->db = Database::getInstance();
        $this->pinyin = new Pinyin();
    }

    public function getAll($categoryId = null) {
        $sql = "
            SELECT s.id,
                   s.name,
                   s.category_id
            FROM user_seasonings s
        ";

        $params = [];

        if ($categoryId !== null) {
            $sql .= " WHERE s.category_id = ?";
            $params[] = $categoryId;
        }

        $sql .= " ORDER BY s.category_id ASC, s.pinyin ASC";

        return $this->db->query($sql, $params);
    }
    public function findById($id) {
        $sql = "
            SELECT id, name, category_id
            FROM user_seasonings
            WHERE id = ?
        ";

        return $this->db->queryOne($sql, [$id]);
    }
    public function findByRecipe($recipeId) {
        $sql = "
            SELECT i.id, i.name, i.category_id, rs.quantity
            FROM user_seasonings i
            JOIN user_recipe_seasonings rs ON i.id = rs.seasoning_id
            WHERE rs.recipe_id = ?
            ORDER BY i.category_id ASC, i.pinyin ASC
        ";

        return $this->db->query($sql, [$recipeId]);
    }

    public function insert($name, $categoryId) {
        $pinyin = $this->pinyin->permalink($name, '');
        $categoryId = isset($categoryId) && $categoryId !== ''
            ? intval($categoryId)
            : 1;
        $this->db->execute(
            "INSERT INTO user_seasonings (name, pinyin, category_id) VALUES (?, ?, ?)",
            [$name, $pinyin, $categoryId]
        );

        return $this->db->lastInsertId();
    }

    public function update($id, $name, $categoryId) {
        $pinyin = $this->pinyin->permalink($name, '');
        $this->db->execute(
            "UPDATE user_seasonings
             SET name = ?, category_id = ?, pinyin = ?
             WHERE id = ?",
            [$name, $categoryId, $pinyin, $id]
        );
    }

    public function delete($id) {
        $this->db->execute(
            "DELETE FROM user_seasonings WHERE id = ?",
            [$id]
        );
    }
}
