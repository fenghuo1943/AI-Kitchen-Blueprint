<?php
namespace App\Controllers\Api;

use App\Services\HistoryService;
use App\Core\Response;
use App\Middleware\JWTMiddleware;

class HistoryController
{
    private $service;

    public function __construct()
    {
        $this->service = new HistoryService();
    }

    // GET /api/history
    public function index()
    {
        try {
            $userData = JWTMiddleware::verify();
            if(!$userData){
                return Response::error('未授权',401);
            }
            //$userId = $this->getUserId();
            $userId = $userData->id;
            $page = intval($_GET['page'] ?? 1);
            $pageSize = intval($_GET['pageSize'] ?? 30);
            $data = $this->service->getList($userId, $page, $pageSize);

            Response::success($data);

        } catch (\Throwable $e) {
            Response::error($e->getMessage());
        }
    }

    // POST /api/history
    public function store()
    {
        try {
            $userData = JWTMiddleware::verify();
            if(!$userData){
                return Response::error('未授权',401);
            }
            $input = json_decode(file_get_contents("php://input"), true);
            $userId = $userData->id;
            $this->service->record(
                $userId,
                intval($input['recipe_id'])
            );

            Response::success();

        } catch (\Throwable $e) {
            Response::error($e->getMessage());
        }
    }

    // DELETE /api/history
    public function destroy()
    {
        try {
            $userData = JWTMiddleware::verify();
            if(!$userData){
                return Response::error('未授权',401);
            }
            $userId = $userData->id;
            $this->service->clear($userId);
            Response::success();

        } catch (\Throwable $e) {
            Response::error($e->getMessage());
        }
    }

    private function getUserId()
    {
        return $_SESSION['user_id'] ?? 1;
    }
}