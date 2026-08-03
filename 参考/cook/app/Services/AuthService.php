<?php

namespace App\Services;

use App\Core\Response;
use App\Repositories\UserRepository;
use Firebase\JWT\JWT;
use Firebase\JWT\Key;

class AuthService {
    private $userRepo;
    private $accessKey = "fesbytjhgfewftyhgfecbyyujgfr324753"; // 请替换为复杂随机字符串
    private $refreshKey = "hfuejojiojer489i90ejfoirj3j2ifojoda";

    public function __construct() {
        $this->userRepo = new UserRepository();
    }

    public function login(string $username, string $password): array {

        $user = $this->userRepo->findByUsernameOrEmail($username);

        if (!$user) {
            return ["success" => false, "message" => "用户不存在"];
        }
        if (!password_verify($password, $user['password'])) {
            return ["success" => false, "message" => "密码错误"];
        }
        $tokens = $this->generateTokens($user);

        return [
            "success" => true,
            "accessToken" => $tokens["accessToken"],
            "refreshToken" => $tokens["refreshToken"],
            "message" => "登录成功"
        ];
    }
    public function refresh(string $refreshToken) {
        try {
            $decoded = JWT::decode($refreshToken, new Key($this->refreshKey, 'HS256'));
            $user = json_decode(json_encode($decoded->data), true);
            // 刷新 token
            return $this->generateTokens($user);
        }catch (\Exception $e) {
            http_response_code(401);
            return Response::error('refreshToken 无效', 401);
        }
    }
    private function generateTokens($user) {
        $time = time();
        $accessPayload = [
            "iss" => "recipe-website",
            'iat' => $time,
            'exp' => $time + 3600 * 24 * 7,
            'data' => [
                "id" => $user['id'],
                "username" => $user['username']
            ]
        ];
        $refreshPayload = [
            "iss" => "recipe-website",
            'iat' => $time,
            'exp' => $time + 70 * 24 * 3600, // 7天
            'data' => [
                "id" => $user['id'],
                "username" => $user['username']
            ]
        ];

        $accessToken = JWT::encode($accessPayload, $this->accessKey, 'HS256');
        $refreshToken = JWT::encode($refreshPayload, $this->refreshKey, 'HS256');
        return [
            "accessToken" => $accessToken,
            "refreshToken" => $refreshToken
        ];
    }

    public function register(string $username, string $email, string $password): array {
        if ($this->userRepo->exists($username, $email)) {
            return ["success" => false, "message" => "用户名或邮箱已存在"];
        }

        $hashed = password_hash($password, PASSWORD_BCRYPT);
        $this->userRepo->create($username, $email, $hashed);

        return ["success" => true, "message" => "注册成功"];
    }

    public function getUserById(int $id) {
        return $this->userRepo->getById($id);
    }
}
