<?php
namespace App\Repositories;

use App\Core\Database;

class CategoryRepository
{
    private $db;

    private $typeMap = [
        'ingredient' => 'user_ing_categories',
        'recipe'     => 'user_categories',
        'seasoning'  => 'user_seasoning_categories',
    ];

    public function __construct()
    {
        $this->db = Database::getInstance();
    }

    private function getTable($type)
    {
        if (!isset($this->typeMap[$type])) {
            throw new \Exception("非法分类类型");
        }

        return $this->typeMap[$type];
    }

    public function getAll($type)
    {
        $table = $this->getTable($type);

        return $this->db->query("
            SELECT id, name
            FROM {$table}
            ORDER BY id ASC
        ");
    }
    public function findById($type, $id)
    {      $table = $this->getTable($type);

        return $this->db->queryOne(
            "SELECT id, name FROM {$table} WHERE id = ?",
            [$id]
        );
    }
    public function findByRecipe($recipeId)
    {

        return $this->db->query(
            "SELECT c.id, c.name
             FROM user_categories c
             JOIN user_recipe_categories rc ON c.id = rc.category_id
             WHERE rc.recipe_id = ?",
            [$recipeId]
        );
    }
    public function findByIngredient($ingredientId)
    {
        return $this->db->query(
            "SELECT c.id, c.name
             FROM user_ing_categories c
             JOIN user_ingredient_categories ic ON c.id = ic.category_id
             WHERE ic.ingredient_id = ?",
            [$ingredientId]
        );
    }
    public function findBySeasoning($seasoningId)
    {
        return $this->db->query(
            "SELECT c.id, c.name
             FROM user_seasoning_categories c
             JOIN user_seasoning_categories_seasonings sc ON c.id = sc.category_id
             WHERE sc.seasoning_id = ?",
            [$seasoningId]
        );
    }

    public function insert($type, $name)
    {
        $table = $this->getTable($type);

        $this->db->execute(
            "INSERT INTO {$table} (name) VALUES (?)",
            [$name]
        );

        return $this->db->lastInsertId();
    }

    public function update($type, $id, $name)
    {
        $table = $this->getTable($type);

        $this->db->execute(
            "UPDATE {$table} SET name=? WHERE id=?",
            [$name, $id]
        );
    }

    public function delete($type, $id)
    {
        $table = $this->getTable($type);

        $this->db->execute(
            "DELETE FROM {$table} WHERE id=?",
            [$id]
        );
    }
}