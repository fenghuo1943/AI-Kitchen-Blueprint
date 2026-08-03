<?php

namespace App\Repositories;

use App\Core\Database;

class RecipeCategoryRepository {
    private $db;

    public function __construct() {
        $this->db = Database::getInstance();
    }
    public function findByRecipe($recipeId) {
        return $this->db->query(
            "SELECT id, recipe_id, category_id
             FROM user_recipe_categories
             WHERE recipe_id = ?",
            [$recipeId]
        );
    }
    public function findById($categoryId) {
        return $this->db->query(
            "SELECT id, recipe_id, category_id
             FROM user_recipe_categories
             WHERE category_id = ?",
            [$categoryId]
        );
    }
    public function insert($recipeId, $categoryId) {
        $this->db->execute(
            "INSERT INTO user_recipe_categories (recipe_id,category_id) VALUES (?,?)",
            [$recipeId, $categoryId]
        );
    }
    public function delete($recipeId, $categoryId) {
        $this->db->execute(
            "DELETE FROM user_recipe_categories WHERE recipe_id=? AND category_id=?",
            [$recipeId, $categoryId]
        );
    }
    public function deleteByRecipe($recipeId) {
        $this->db->execute(
            "DELETE FROM user_recipe_categories WHERE recipe_id=?",
            [$recipeId]
        );
    }
}
