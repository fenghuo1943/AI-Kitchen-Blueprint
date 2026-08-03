<?php

namespace App\Controllers\Api;

use App\Services\RecipeService;
use App\Services\HistoryService;
use App\Core\Response;
use App\Middleware\JWTMiddleware;

ini_set('display_errors', 1);
error_reporting(E_ALL);

/**
 * ============================================================
 * 菜谱 REST API
 * Base URL: /api/recipe
 * ============================================================
 */
class RecipeController {

    private $service;
    private $historyService;
    private $zbp;

    public function __construct($zbp = null) {
        $this->service = new RecipeService();
        $this->historyService = new HistoryService();
        $this->zbp = $zbp;
    }

    /**
     * ------------------------------------------------------------
     * GET /api/recipe
     * ------------------------------------------------------------
     * 查询菜谱列表（支持多条件筛选）
     *
     * 示例：
     * GET /api/recipe
     * GET /api/recipe?ingredients=1,2,3
     * GET /api/recipe?category=5
     * GET /api/recipe?q=鸡肉
     * GET /api/recipe?page=2&pageSize=20
     * GET /api/recipe?deleted=1
     *
     * 参数说明：
     * ingredients : 食材ID数组 (逗号分隔)
     * category    : 分类ID
     * match       : 匹配模式 exact|fuzzy
     * q           : 关键词
     * page        : 页码
     * pageSize    : 每页数量
     * deleted     : 1=已删除（回收站）
     */
    public function index() {
        try {
            $userData = JWTMiddleware::verify();
            if(!$userData){
                return Response::error('未授权',401);
            }
            $ingredients = isset($_GET['ingredients'])
                ? array_filter(array_map('intval', explode(',', $_GET['ingredients'])))
                : [];
            $categoryId = isset($_GET['category']) ? intval($_GET['category']) : null;
            $matchMode = $_GET['match'] ?? 'exact';
            $keyword = trim($_GET['q'] ?? '');
            $page = intval($_GET['page'] ?? 1);
            $pageSize = intval($_GET['pageSize'] ?? 10);
            $sort=$_GET['sort'] ?? 'score';
            $order=$_GET['order'] ?? 'desc';
            $deleted   = isset($_GET['deleted']) && $_GET['deleted'] == 1;

            $data = $this->service->searchRecipes(
                $userId = $userData->id,
                $ingredients,
                $categoryId,
                $matchMode,
                $keyword,
                $page,
                $pageSize,
                $sort,$order,
                $deleted
        );
            Response::success($data);
        } catch (\Throwable $e) {
            Response::error($e->getMessage());
        }
    }

    /**
     * ------------------------------------------------------------
     * GET /api/recipe/{id}
     * ------------------------------------------------------------
     * 获取单个菜谱详情
     *
     * 示例：
     * GET /api/recipe/1
     *
     * 返回：
     * recipe       基本信息
     * ingredients  食材列表
     * steps        步骤列表
     * is_favorite  是否收藏
     */
    public function show($id) {
        try {
            //$userId = $this->getUserId();
            $userData = JWTMiddleware::verify();
            if(!$userData){
                return Response::error('未授权',401);
            }
            $userId = $userData->id;
            $this->historyService->record($userId, $id);
            $recipe = $this->service->getRecipeById($userId, $id);
            if (!$recipe) {
                Response::error('菜谱不存在');
                return;
            }
            /*             $isFavorite = $this->service->isFavorite($userId, $id);
            $recipe['is_favorite'] = $isFavorite;
            $recipe['user_logged_in'] = $userId > 0; */
            Response::success($recipe);
        } catch (\Throwable $e) {
            Response::error($e->getMessage());
        }
    }

    /**
     * ------------------------------------------------------------
     * POST /api/recipe
     * ------------------------------------------------------------
     * 新增菜谱
     *
     * Content-Type: application/json
     *
     * 示例：
     * POST /api/recipe
     *
     * Body:
     * {
     *   "title": "红烧肉",
     *   "cook_time": 40,
     *   "ingredients": [...],
     *   "steps": [...]
     * }
     */
    public function store() {
        try {
            $userData = JWTMiddleware::verify();
            if(!$userData){
                return Response::error('未授权',401);
            }
            $input = json_decode(file_get_contents("php://input"), true);
            if (empty($input)) {
                Response::error('提交数据不能为空');
                return;
            }
            $recipeId = $this->service->saveRecipe(
                $input,
                $userData->id
            );
            Response::success([
                'id' => $recipeId,
                'message' => '菜谱创建成功'
            ]);
        } catch (\Throwable $e) {
            Response::error($e->getMessage());
        }
    }

    /**
     * ------------------------------------------------------------
     * PUT /api/recipe/{id}
     * ------------------------------------------------------------
     * 更新菜谱
     *
     * Content-Type: application/json
     *
     * 示例：
     * PUT /api/recipe/1
     *
     * Body:
     * {
     *   "title": "修改后的红烧肉"
     * }
     */
    public function update($id) {
        try {
            $userData = JWTMiddleware::verify();
            if(!$userData){
                return Response::error('未授权',401);
            }
            $input = json_decode(file_get_contents("php://input"), true);

            $recipeId = $this->service->saveRecipe(
                $input,
                $userData->id,
                $id
            );

            Response::success(['id' => $recipeId]);
        } catch (\Throwable $e) {
            Response::error($e->getMessage());
        }
    }

    /**
     * ------------------------------------------------------------
     * DELETE /api/recipe/{id}
     * ------------------------------------------------------------
     * 软删除菜谱（进入回收站）
     *
     * 示例：
     * DELETE /api/recipe/1
     */
    public function destroy($id) {
        try {
            $userData = JWTMiddleware::verify();
            if(!$userData){
                return Response::error('未授权',401);
            }
            $this->service->softDelete($id);
            Response::success();
        } catch (\Throwable $e) {
            Response::error($e->getMessage());
        }
    }

    /**
     * ------------------------------------------------------------
     * DELETE /api/recipe/{id}?forever=1
     * ------------------------------------------------------------
     * 彻底删除菜谱
     *
     * 示例：
     * DELETE /api/recipe/1?forever=1
     */
    public function destroyForever($id) {
        try {
            $userData = JWTMiddleware::verify();
            if(!$userData){
                return Response::error('未授权',401);
            }
            $this->service->delete($id);
            Response::success();
        } catch (\Throwable $e) {
            Response::error($e->getMessage());
        }
    }

    /**
     * ------------------------------------------------------------
     * POST /api/recipe/{id}/restore
     * ------------------------------------------------------------
     * 恢复菜谱
     *
     * 示例：
     * POST /api/recipe/1/restore
     */
    public function restore($id) {
        try {
            $userData = JWTMiddleware::verify();
            if(!$userData){
                return Response::error('未授权',401);
            }
            $this->service->restore($id);
            Response::success();
        } catch (\Throwable $e) {
            Response::error($e->getMessage());
        }
    }

    private function getUserId() {
        if ($this->zbp->user->ID) {
            return $this->zbp->user->ID;
        } else {
            return 1;
        }
    }
}
