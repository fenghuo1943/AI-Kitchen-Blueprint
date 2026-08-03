<?php

namespace App\Repositories;

use App\Core\Database;

class RecipeStepRepository {
    private $db;

    public function __construct() {
        $this->db = Database::getInstance();
    }
    public function findByRecipe($recipeId) {
        return $this->db->query(
            "SELECT id, recipe_id, step_order, content
             FROM user_steps
             WHERE recipe_id = ?
             ORDER BY step_order ASC",
            [$recipeId]
        );
    }
    public function findByOrder($recipeId,$stepOrder) {
        return $this->db->query(
            "SELECT id, recipe_id, step_order, content
             FROM user_steps
             WHERE step_order = ? AND recipe_id = ?",
            [$stepOrder, $recipeId]
        );
    }
    public function insert($recipeId, $order, $content) {
        $this->db->execute(
            "INSERT INTO user_steps (recipe_id,step_order,content) VALUES (?,?,?)",
            [$recipeId, $order, $content]
        );
    }
    public function delete($recipeId, $stepOrder) {
        $this->db->execute(
            "DELETE FROM user_steps WHERE recipe_id=? AND step_order=?",
            [$recipeId, $stepOrder]
        );
    }
    public function deleteByRecipe($recipeId) {
        $this->db->execute(
            "DELETE FROM user_steps WHERE recipe_id=?",
            [$recipeId]
        );
    }
}
