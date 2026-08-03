<?php

namespace App\Controllers\Api;

use App\Core\Response;
use App\Services\AuthService;

class UserController {
    private $zbp;
    private $authService;
    public function __construct($zbp = null) {
        $this->zbp = $zbp;
        $this->authService = new AuthService();
    }

    // GET /api/favorite
    public function index() {
        try {
            $userId = $this->getUserId();


            Response::success($userId);
        } catch (\Throwable $e) {
            Response::error($e->getMessage());
        }
    }


    private function getUserId() {
        if ($this->zbp->user->ID) {
            return $this->zbp->user->ID;
        } else {
            return 0;
        }
    }
    public function login()
    {
        header('Content-Type: application/json');
        $data = json_decode(file_get_contents("php://input"), true);
        $username = trim($data['username'] ?? '');
        $password = trim($data['password'] ?? '');

        if (!$username || !$password) {
            echo json_encode(["success" => false, "message" => "用户名或密码不能为空"]);
            return;
        }

        $result = $this->authService->login($username, $password);
        echo json_encode($result);
    }

    public function register()
    {
        header('Content-Type: application/json');
        $data = json_decode(file_get_contents("php://input"), true);
        $username = trim($data['username'] ?? '');
        $email = trim($data['email'] ?? '');
        $password = trim($data['password'] ?? '');

        if (!$username || !$email || !$password) {
            echo json_encode(["success" => false, "message" => "请填写完整信息"]);
            return;
        }

        $result = $this->authService->register($username, $email, $password);
        echo json_encode($result);
    }
}
