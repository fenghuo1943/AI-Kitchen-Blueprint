<?php

namespace App\Repositories;

use App\Core\Database;
use Overtrue\Pinyin\Pinyin;

class RecipeRepository {
    private $db;
    private $pinyin;
    public function __construct() {
        $this->db = Database::getInstance();
        $this->pinyin = new Pinyin();
    }

    public function findById(int $id): ?array {
        return $this->db->queryOne(
            "SELECT id, user_id, title, description, cook_time, created_at, updated_at
             FROM user_recipes
             WHERE id = ?",
            [$id]
        );
    }
    public function insert(array $data): int {
        $cookTime = $data['cook_time'] ?? null;
        $pinyinTitle = $this->pinyin->permalink($data['title'], '');
        // 关键修正
        if ($cookTime === '' || $cookTime === null) {
            $cookTime = null;
        } else {
            $cookTime = (int)$cookTime;
        }
        $sql = "
            INSERT INTO user_recipes
            (user_id, title, description, cook_time, pinyin, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, NOW(), NOW())
        ";

        $this->db->execute($sql, [
            $data['user_id'],
            $data['title'],
            $data['description'] ?? '',
            $cookTime,
            $pinyinTitle
        ]);

        return (int)$this->db->getConnection()->lastInsertId();
    }
    public function update(int $id, array $data): bool {
        $cookTime = $data['cook_time'] ?? null;
        $pinyinTitle = $this->pinyin->permalink($data['title'], '');
        // 关键修正
        if ($cookTime === '' || $cookTime === null) {
            $cookTime = null;
        } else {
            $cookTime = (int)$cookTime;
        }
        $sql = "
            UPDATE user_recipes
            SET title = ?, description = ?, cook_time = ?, pinyin = ?, updated_at = NOW()
            WHERE id = ?
        ";

        return (bool)$this->db->execute($sql, [
            $data['title'],
            $data['description'] ?? '',
            $cookTime,
            $pinyinTitle,
            $id,
        ]);
    }
    public function softDelete(int $id): bool {
        return (bool)$this->db->execute(
            "UPDATE user_recipes SET deleted_at = NOW() WHERE id = ?",
            [$id]
        );
    }
    public function delete(int $id): bool {
        return (bool)$this->db->execute(
            "DELETE FROM user_recipes WHERE id = ?",
            [$id]
        );
    }
    public function restore(int $id): bool {
        return (bool)$this->db->execute(
            "UPDATE user_recipes SET deleted_at = NULL WHERE id = ?",
            [$id]
        );
    }
    

    
    /* =============================
       分页（纯分页，不做复杂 join）
    ============================== */
    public function paginate(int $offset, int $limit): array {
        return $this->db->query(
            "SELECT id, title, cook_time, created_at
             FROM user_recipes
             WHERE deleted_at IS NULL
             ORDER BY created_at DESC
             LIMIT ?, ?",
            [$offset, $limit]
        );
    }
    public function count(): int {
        $row = $this->db->queryOne(
            "SELECT COUNT(*) AS total
             FROM user_recipes
             WHERE deleted_at IS NULL"
        );

        return (int)($row['total'] ?? 0);
    }
}
