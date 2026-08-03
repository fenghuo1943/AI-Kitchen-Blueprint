<?php

namespace App\Controllers\Api;

use App\Services\CategoryService;
use App\Core\Response;
use App\Middleware\JWTMiddleware;

class CategoryController {
    private $service;
    private $jwtMiddleware;

    public function __construct() {
        $this->service = new CategoryService();
        $this->jwtMiddleware = new JWTMiddleware();
    }

    public function index() {
        try {
            $type = $_GET['type'] ?? null;

            if (!$type) {
                throw new \Exception("缺少分类类型");
            }
            $data = $this->service->getAll($type);
            Response::success($data);
        } catch (\Throwable $e) {
            Response::error($e->getMessage());
        }
    }

    public function store() {
        try {
            $type = $_GET['type'] ?? null;
            $input = json_decode(file_get_contents("php://input"), true);
            if (empty($type)) {
                throw new \Exception("缺少分类类型");
            }
            
            $userData = JWTMiddleware::verify();
            if(!$userData){
                return Response::error('未授权',401);
            }
            if (empty($input['name'])) {
                throw new \Exception("分类名称不能为空");
            }
            $id = $this->service->create($type, $input['name']);
            Response::success(['id' => $id]);
        } catch (\Throwable $e) {
            // 捕获唯一索引异常并返回 code=0
            if ($e instanceof \PDOException && $e->getCode() == '23000') {
                Response::error('分类名已存在！'); // code=0
            } else {
                Response::error($e->getMessage()); // code=0
            }
        }
    }

    public function update($id) {
        try {
            $userData = JWTMiddleware::verify();
            if(!$userData){
                return Response::error('未授权',401);
            }
            $type = $_GET['type'] ?? null;
            $input = json_decode(file_get_contents("php://input"), true);
            if (empty($type)) {
                throw new \Exception("缺少分类类型");
            }

            if (empty($input['name'])) {
                throw new \Exception("分类名称不能为空");
            }
            $this->service->update($type, $id, $input['name']);

            Response::success();
        } catch (\Throwable $e) {
            Response::error($e->getMessage());
        }
    }

    public function destroy($id) {
        try {
            $userData = JWTMiddleware::verify();
            if(!$userData){
                return Response::error('未授权',401);
            }
            if (!$id) {
                Response::error('ID is required');
                return;
            }
            $type = $_GET['type'] ?? null;
            $this->service->delete($type, $id);

            Response::success();
        } catch (\Throwable $e) {
            Response::error($e->getMessage());
        }
    }
}
