<?php
namespace App\Middleware;

use App\Core\Response;
use Firebase\JWT\JWT;
use Firebase\JWT\Key;

class JWTMiddleware
{
    private static $accessKey = "fesbytjhgfewftyhgfecbyyujgfr324753"; // 与 AuthService 中保持一致

    /**
     * 验证请求的 Authorization Bearer Token
     * 成功返回用户数据，失败直接输出 401 JSON 并 exit
     */
    public static function verify()
    {
        $headers = getallheaders();
        $authHeader = $headers['Authorization'] ?? '';
        if (!$authHeader || !preg_match('/Bearer\s(\S+)/', $authHeader, $matches)) {
            http_response_code(401);
            return Response::error('未授权');
        }

        $token = $matches[1];
        try {
            $decoded = JWT::decode($token, new Key(self::$accessKey, 'HS256'));
            //$result=
            return $decoded->data; // 返回 token 中的用户数据
        } catch (\Exception $e) {
            http_response_code(401);
            return Response::error('Token 无效或已过期');
        }
    }
}