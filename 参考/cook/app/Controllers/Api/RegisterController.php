<?php
namespace App\Controllers\Api;

use App\Core\Response;
use App\Services\AuthService;

class RegisterController
{
    private $authService;

    public function __construct($zbp = null)
    {
        $this->authService = new AuthService();
    }

    /**
     * POST /api/register -> store
     */
    public function store()
    {
        header('Content-Type: application/json');
        $data = json_decode(file_get_contents("php://input"), true);
        $username = trim($data['username'] ?? '');
        $email = trim($data['email'] ?? '');
        $password = trim($data['password'] ?? '');
        if (!$username || !$email || !$password) {
            echo json_encode(['success'=>false, 'message'=>'请填写完整信息']);
            return;
        }
        $result = $this->authService->register($username, $email, $password);
        return Response::success(msg:$result['message']);
    }
}