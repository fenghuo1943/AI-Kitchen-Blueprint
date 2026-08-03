<?php

namespace App\Repositories;

use App\Core\Database;
use Overtrue\Pinyin\Pinyin;

class IngredientRepository {
    private $db;
    private $pinyin;

    public function __construct() {
        $this->db = Database::getInstance();
        $this->pinyin = new Pinyin();
    }

    public function getAll() {
        $sql = "
            SELECT id, name, category_id
            FROM user_ingredients
            ORDER BY category_id ASC, pinyin ASC
        ";

        return $this->db->query($sql);
    }
    public function findById($id) {
        $sql = "
            SELECT id, name, category_id
            FROM user_ingredients
            WHERE id = ?
        ";

        return $this->db->queryOne($sql, [$id]);
    }
    public function findByRecipe($recipeId) {
        $sql = "
            SELECT i.id, i.name, i.category_id, ri.quantity
            FROM user_ingredients i
            JOIN user_recipe_ingredients ri ON i.id = ri.ingredient_id
            WHERE ri.recipe_id = ?
            ORDER BY i.category_id ASC, i.pinyin ASC
        ";

        return $this->db->query($sql, [$recipeId]);
    }

    public function insert($name, $categoryId) {
        $pinyinName = $this->pinyin->permalink($name, '');
        $sql = "INSERT INTO user_ingredients (name, category_id, pinyin) VALUES (?, ?, ?)";
        $this->db->execute($sql, [$name, $categoryId, $pinyinName]);
        return $this->db->lastInsertId();
    }
    public function update($id, $name, $categoryId) {
        $pinyinName = $this->pinyin->permalink($name, '');
         $sql = "UPDATE user_ingredients SET name=?, category_id=?, pinyin=? WHERE id=?";
        $this->db->execute($sql, [$name, $categoryId, $pinyinName, $id]);
    }
    public function delete($id) {
        $sql = "DELETE FROM user_ingredients WHERE id=?";
        $this->db->execute($sql, [$id]);
    }
}