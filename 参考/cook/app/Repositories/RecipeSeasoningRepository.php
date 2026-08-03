<?php

namespace App\Repositories;

use App\Core\Database;

class RecipeSeasoningRepository {
    private $db;

    public function __construct() {
        $this->db = Database::getInstance();
    }
    public function findByRecipe($recipeId) {
        return $this->db->query(
            "SELECT id, recipe_id, seasoning_id, quantity
                FROM user_recipe_seasonings
                WHERE recipe_id = ?",
            [$recipeId]
        );
    }
    public function findById($seasoningId) {
        return $this->db->query(
            "SELECT id, recipe_id, seasoning_id, quantity
                FROM user_recipe_seasonings
                WHERE seasoning_id = ?",
            [$seasoningId]
        );
    }
    public function insert($recipeId, $seasoningId, $quantity = null) {
        $this->db->execute(
            "INSERT INTO user_recipe_seasonings (recipe_id,seasoning_id,quantity) VALUES (?,?,?)",
            [$recipeId, $seasoningId, $quantity]
        );
    }
    public function delete($recipeId, $seasoningId) {
        $this->db->execute(
            "DELETE FROM user_recipe_seasonings WHERE recipe_id=? AND seasoning_id=?",
            [$recipeId, $seasoningId]
        );
    }
    public function deleteByRecipe($recipeId) {
        $this->db->execute(
            "DELETE FROM user_recipe_seasonings WHERE recipe_id=?",
            [$recipeId]
        );
    }
}
