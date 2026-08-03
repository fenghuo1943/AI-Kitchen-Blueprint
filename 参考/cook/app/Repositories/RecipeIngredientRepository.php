<?php

namespace App\Repositories;

use App\Core\Database;

class RecipeIngredientRepository {
    private $db;

    public function __construct() {
        $this->db = Database::getInstance();
    }
    public function findByRecipe($recipeId) {
        return $this->db->query(
            "SELECT id, recipe_id, ingredient_id, quantity
             FROM user_recipe_ingredients
             WHERE recipe_id = ?",
            [$recipeId]
        );
    }
    public function findById($ingId){
        return $this->db->query(
            "SELECT id, recipe_id, ingredient_id, quantity
             FROM user_recipe_ingredients
             WHERE ingredient_id = ?",
            [$ingId]
        );
    }
    public function insert($recipeId, $ingredientId, $quantity = null) {
        $this->db->execute(
            "INSERT INTO user_recipe_ingredients (recipe_id,ingredient_id,quantity) VALUES (?,?,?)",
            [$recipeId, $ingredientId, $quantity]
        );
    }
    public function delete($recipeId, $ingredientId) {
        $this->db->execute(
            "DELETE FROM user_recipe_ingredients WHERE recipe_id=? AND ingredient_id=?",
            [$recipeId, $ingredientId]
        );
    }
    public function deleteByRecipe($recipeId) {
        $this->db->execute(
            "DELETE FROM user_recipe_ingredients WHERE recipe_id=?",
            [$recipeId]
        );
    }
}
