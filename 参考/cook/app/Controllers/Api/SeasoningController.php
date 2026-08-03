<?php

namespace App\Controllers\Api;

use App\Services\SeasoningService;
use App\Core\Response;

class SeasoningController {
    private $service;

    public function __construct() {
        $this->service = new SeasoningService();
    }

    // GET /api/seasoning?category_id=1
    public function index() {
        try {
            $categoryId = isset($_GET['categoryId'])
                ? intval($_GET['categoryId'])
                : null;

            $data = $this->service->getList($categoryId);

            Response::success($data);
        } catch (\Throwable $e) {
            Response::error($e->getMessage());
        }
    }

    // POST /api/seasoning
    public function store() {
        try {
            $input = json_decode(file_get_contents("php://input"), true);
            if (empty($input['name'])) {
                throw new \Exception("调料名称不能为空");
            }

            $categoryId = isset($input['categoryId']) && $input['categoryId'] !== ''
                ? intval($input['categoryId'])
                : 1;
            $id = $this->service->create($input['name'], $categoryId);

            Response::success(['id' => $id]);
        } catch (\Throwable $e) {
            Response::error($e->getMessage());
        }
    }

    // PUT /api/seasoning/{id}
    public function update($id) {
        try {
            $input = json_decode(file_get_contents("php://input"), true);
            //echo json_encode($input);
            if (empty($input['name'])) {
                throw new \Exception("调料名称不能为空");
            }
            $categoryId = isset($input['categoryId']) && $input['categoryId'] !== ''
                ? intval($input['categoryId'])
                : 1;
            $this->service->update($id, $input['name'], $categoryId);

            Response::success();
        } catch (\Throwable $e) {
            Response::error($e->getMessage());
        }
    }

    // DELETE /api/seasoning/{id}
    public function destroy($id) {
        try {
            $this->service->delete($id);

            Response::success();
        } catch (\Throwable $e) {
            Response::error($e->getMessage());
        }
    }
}
