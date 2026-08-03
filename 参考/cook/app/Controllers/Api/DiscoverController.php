<?php
namespace App\Controllers\Api;

use App\Services\DiscoverService;
use App\Core\Response;
use App\Middleware\JWTMiddleware;

class DiscoverController
{
    private $service;

    public function __construct()
    {
        $this->service = new DiscoverService();
    }

    // GET /api/history
    public function index()
    {
        try {
            $userId = $this->getUserId();
            $userData = JWTMiddleware::verify();
            if(!$userData){
                return Response::error('未授权',401);
            }
            $userId = $userData->id;
            $type = $_GET['type'] ?? 'today'; // 默认今日推荐
            $limit = $_GET['limit'] ?? 6;
            switch ($type) {
            case 'today':
                $data = $this->service->getTodayRecommend($userId, (int)$limit);
                break;
            case 'hot':
                $data = $this->service->getHotRecipes($userId, (int)$limit);
                break;
            case 'new':
                $data = $this->service->getNewRecipes($userId,(int)$limit);
                break;
            case 'random':
                $data = $this->service->getRandomRecipes($userId,(int)$limit);
                break;
            default:
                Response::error("Invalid type");
                return;
        }
            Response::success($data);

        } catch (\Throwable $e) {
            Response::error($e->getMessage());
        }
    }

    
    private function getUserId()
    {
        return $_SESSION['user_id'] ?? 1;
    }
}