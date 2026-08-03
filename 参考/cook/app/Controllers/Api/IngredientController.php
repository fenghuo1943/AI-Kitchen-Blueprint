<?php

namespace App\Controllers\Api;

use App\Services\IngredientService;
use App\Core\Response;
use App\Middleware\JWTMiddleware;

class IngredientController {
    private $service;

    public function __construct() {
        $this->service = new IngredientService();
    }

    public function index() {
        $data = $this->service->getIngredients();
        Response::success($data);
    }
    public function store() {
        try {
            $userData = JWTMiddleware::verify();
            if(!$userData){
                return Response::error('未授权',401);
            }
            $input = json_decode(file_get_contents("php://input"), true);

            if (empty($input['name'])) {
                \App\Core\Response::error('食材名不能为空');
            }
            
            $categoryId = isset($input['categoryId']) && $input['categoryId'] !== ''
                ? intval($input['categoryId'])
                : 1;
            $id = $this->service->create($input['name'], $categoryId);
            Response::success(['id' => $id, 'name' => $input['name'], 'categoryId' => $categoryId]);
        } catch (\Throwable $e) {
            Response::error($e->getMessage());
        }
    }
    public function update($id) {
        try {
            $userData = JWTMiddleware::verify();
            if(!$userData){
                return Response::error('未授权',401);
            }
            $input = json_decode(file_get_contents("php://input"), true);
            $name = $input['name'];
            if (empty($name)) {
                throw new \Exception('食材名不能为空');
            }
            $categoryId = isset($input['categoryId']) && $input['categoryId'] !== ''
                ? intval($input['categoryId'])
                : null;
            $this->service->update($id, $name, $categoryId);
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
            $this->service->delete($id);
            Response::success();
        } catch (\Throwable $e) {
            Response::error($e->getMessage());
        }
    }
}
