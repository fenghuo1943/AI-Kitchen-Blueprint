<?php
namespace App\Repositories;

use App\Core\Database;

class StepRepository
{
    private $db;

    public function __construct()
    {
        $this->db = Database::getInstance();
    }

    public function getByRecipe($recipeId)
    {
        return $this->db->query(
            "SELECT id, recipe_id, step_order, content, image
             FROM user_steps
             WHERE recipe_id = ?
             ORDER BY step_order ASC",
            [$recipeId]
        );
    }

    public function insert($recipeId, $stepOrder, $content, $image)
    {
        $this->db->execute(
            "INSERT INTO user_steps
             (recipe_id, step_order, content, image)
             VALUES (?, ?, ?, ?)",
            [$recipeId, $stepOrder, $content, $image]
        );

        return $this->db->lastInsertId();
    }

    public function update($id, $stepOrder, $content, $image)
    {
        $this->db->execute(
            "UPDATE user_steps
             SET step_order = ?, content = ?, image = ?
             WHERE id = ?",
            [$stepOrder, $content, $image, $id]
        );
    }

    public function delete($id)
    {
        $this->db->execute(
            "DELETE FROM user_steps WHERE id = ?",
            [$id]
        );
    }

    public function deleteByRecipe($recipeId)
    {
        $this->db->execute(
            "DELETE FROM user_steps WHERE recipe_id = ?",
            [$recipeId]
        );
    }
}