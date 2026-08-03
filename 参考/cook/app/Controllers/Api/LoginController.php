<?php

namespace App\Controllers\Api;

use App\Core\Response;
use App\Services\AuthService;

ini_set('display_errors', 1);
error_reporting(E_ALL);

class LoginController {
    private $authService;

    public function __construct($zbp = null) {
        $this->authService = new AuthService();
    }

    /**
     * POST /api/login -> store
     */
    public function store() {
        header('Content-Type: application/json');
        $data = json_decode(file_get_contents("php://input"), true);
        if (!is_array($data)) {
            return Response::error('请求数据格式错误');
            echo json_encode(['success' => false, 'message' => '请求数据格式错误']);
            return;
        }

        $username = trim($data['username'] ?? '');
        $password = trim($data['password'] ?? '');
        if (!$username || !$password) {
            return Response::error('用户名或密码不能为空');
            //echo json_encode(['success'=>false, 'message'=>'用户名或密码不能为空']);
            return;
        }
        $result = $this->authService->login($username, $password);
        return Response::success(
            [
                'accessToken' => $result['accessToken'],
                'refreshToken' => $result['refreshToken']
            ],
            $result['message']
        );
        echo json_encode($result);
    }

    // 可选：未来需要支持 PUT/DELETE/restore 方法，可按 REST 映射添加
}
