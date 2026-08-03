<?php

namespace App\Controllers\Api;

use App\Services\MenuService;
use App\Core\Response;
use App\Middleware\JWTMiddleware;

class MenuController {
    private MenuService $service;
    private $zbp;

    public function __construct($zbp = null) {
        $this->service = new MenuService();
        $this->zbp = $zbp;
    }

    /**
     * GET /api/menu
     * ?mode=waterfall
     * ?mode=single&date=2026-03-04
     */
    public function index() {
        try {
            $userData = JWTMiddleware::verify();
            if (!$userData) {
                return Response::error('未授权', 401);
            }
            //$userId = $_SESSION['user_id'] ?? 1;
            $userId = $userData->id;
            // 月份查询（用于日历红点）
            if (isset($_GET['month'])) {
                $month = $_GET['month']; // 格式：2026-03
                $dates = $this->service->getMonthDates($userId, $month);
                Response::success([
                    'dates' => $dates
                ]);
                return;
            }
            $mode = $_GET['mode'] ?? 'single';
            $date = $_GET['date'] ?? null;
            if ($mode === 'waterfall') {
                $page = intval($_GET['page'] ?? 1);
                $pageSize = intval($_GET['pageSize'] ?? 10);
                $list = $this->service->getWaterfall($userId, $page, $pageSize);
                Response::success($list);
                return;
            }
            if ($mode === 'single' && $date) {
                $list = $this->service->getByDate($userId, $date);
                $ingList = $this->service->getIngredientsByDate($userId, $date);
                $seaList = $this->service->getSeasoningsByDate($userId, $date);
                Response::success(['list' => $list, 'ingList' => $ingList, 'seaList' => $seaList]);
                return;
            }
            Response::error('请提供日期');
        } catch (\Throwable $e) {
            Response::error($e->getMessage());
        }
    }

    /**
     * POST /api/menu
     * body(JSON):
     * {
     *   "recipe_id": 1,
     *   "date": "2026-03-04"
     * }
     */
    public function store() {
        try {
            $userData = JWTMiddleware::verify();
            if (!$userData) {
                return Response::error('未授权', 401);
            }
            //$userId = $_SESSION['user_id'] ?? 1;
            $userId = $userData->id;
            $input = json_decode(file_get_contents("php://input"), true);
            $recipeId = (int)($input['recipe_id'] ?? 0);
            $date = $input['date'] ?? null;
            if (!$recipeId || !$date) {
                Response::error('参数错误');
                return;
            }
            $this->service->add($userId, $recipeId, $date);
            Response::success();
        } catch (\Throwable $e) {
            Response::error($e->getMessage());
        }
    }

    /**
     * DELETE /api/menu/{recipeId}?date=2026-03-04
     */
    public function destroy($id) {
        try {
            $userData = JWTMiddleware::verify();
            if (!$userData) {
                return Response::error('未授权', 401);
            }
            //$userId = $_SESSION['user_id'] ?? 1;
            $userId = $userData->id;
            $input = json_decode(file_get_contents("php://input"), true);
            $recipeId = (int)($input['recipe_id'] ?? $id ?? 0);
            $date = $input['date'] ?? $_GET['date'] ?? null;
            if (!$recipeId || !$date) {
                Response::error('参数错误');
                return;
            }
            $this->service->remove($userId, (int)$recipeId, $date);
            Response::success();
        } catch (\Throwable $e) {
            Response::error($e->getMessage());
        }
    }
}
