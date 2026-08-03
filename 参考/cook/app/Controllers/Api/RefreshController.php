<?php

namespace App\Controllers\Api;

use App\Core\Response;
use App\Services\AuthService;

class RefreshController {
    private $authService;

    public function __construct($zbp = null)
    {
        $this->authService = new AuthService();
    }
    public function index() {
        $headers = getallheaders();
        $authHeader = $headers['Authorization'] ?? '';

        if (!preg_match('/Bearer\s(\S+)/', $authHeader, $matches)) {
            return Response::error('未授权', 401);
        }
        $refreshToken = $matches[1];
        $tokens = $this->authService->refresh($refreshToken);
        return Response::success($tokens);
    } 
}
