<?php
namespace App\Controllers\Api;

use App\Services\FavoriteService;
use App\Core\Response;
use App\Middleware\JWTMiddleware;

class FavoriteController
{
    private $service;

    public function __construct()
    {
        $this->service = new FavoriteService();
    }

    // GET /api/favorite
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

    // POST /api/favorite
    public function store()
    {
        try {
            $input = json_decode(file_get_contents("php://input"), true);
            $userData = JWTMiddleware::verify();
            if(!$userData){
                return Response::error('未授权',401);
            }
            $userId = $userData->id;
            $this->service->add(
                $userId,
                intval($input['recipe_id'])
            );

            Response::success();

        } catch (\Throwable $e) {
            Response::error($e->getMessage());
        }
    }

    // DELETE /api/favorite/{recipeId}
    public function destroy($recipeId)
    {
        try {
            $userData = JWTMiddleware::verify();
            if(!$userData){
                return Response::error('未授权',401);
            }
            $userId = $userData->id;
            $this->service->remove(
                $userId,
                intval($recipeId)
            );

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