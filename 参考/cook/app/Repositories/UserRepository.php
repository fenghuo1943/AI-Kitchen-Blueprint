<?php
namespace App\Repositories;

use App\Core\Database;
use Firebase\JWT\JWT;

class UserRepository
{
    private $db;

    public function __construct()
    {
        $this->db = Database::getInstance(); // 假设 Database::getInstance() 返回 PDO 封装
    }

    /**
     * 根据用户名或邮箱查找用户
     */
    public function findByUsernameOrEmail(string $username)
    {
        return $this->db->queryOne(
            "SELECT id, username, email, password, created_at
             FROM users
             WHERE username = ? OR email = ?
             LIMIT 1",
            [$username, $username]
        );
    }

    /**
     * 创建用户
     */
    public function create(string $username, string $email, string $hashedPassword)
    {
        $this->db->execute(
            "INSERT INTO users (username, email, password)
             VALUES (?, ?, ?)",
            [$username, $email, $hashedPassword]
        );

        return $this->db->lastInsertId();
    }

    /**
     * 检查用户名或邮箱是否存在
     */
    public function exists(string $username, string $email): bool
    {
        $result = $this->db->queryOne(
            "SELECT id FROM users
             WHERE username = ? OR email = ?
             LIMIT 1",
            [$username, $email]
        );

        return !empty($result);
    }

    /**
     * 根据用户 ID 获取用户信息
     */
    public function getById(int $id)
    {
        return $this->db->queryOne(
            "SELECT id, username, email, created_at
             FROM users
             WHERE id = ?",
            [$id]
        );
    }
}