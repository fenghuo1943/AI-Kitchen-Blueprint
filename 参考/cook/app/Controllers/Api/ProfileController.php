<?php
namespace App\Controllers\Api;

use App\Core\Response;
use App\Services\AuthService;
use App\Middleware\JWTMiddleware;

class ProfileController
{
    private $authService;
    //private $jwtMiddleware;

    public function __construct($zbp = null)
    {
        $this->authService = new AuthService();
        //$this->jwtMiddleware = new JWTMiddleware();
    }

    /**
     * GET /api/profile -> index()
     */
    public function index()
    {
        header('Content-Type: application/json');
        $userData = JWTMiddleware::verify();
        $user = $this->authService->getUserById($userData->id);
        return Response::success($user);
    }

    /**
     * GET /api/profile/{id} -> show($id)
     */
    public function show($id)
    {
        header('Content-Type: application/json');
        $user = $this->authService->getUserById((int)$id);
        if (!$user) {
            return Response::error('用户不存在');
        }
        return Response::success($user);
    }

    // 未来可按 REST 增加 update/destroy/store 方法
}