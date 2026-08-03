<?php
namespace App\Controllers\Api;

use App\Services\StepService;
use App\Core\Response;

class StepController
{
    private $service;

    public function __construct()
    {
        $this->service = new StepService();
    }

    // GET /api/step?recipe_id=1
    public function index()
    {
        try {
            $recipeId = intval($_GET['recipe_id'] ?? 0);

            if (!$recipeId) {
                throw new \Exception("缺少 recipe_id");
            }

            $data = $this->service->getByRecipe($recipeId);

            Response::success($data);

        } catch (\Throwable $e) {
            Response::error($e->getMessage());
        }
    }

    // POST /api/step
    public function store()
    {
        try {
            $input = json_decode(file_get_contents("php://input"), true);

            $id = $this->service->create($input);

            Response::success(['id' => $id]);

        } catch (\Throwable $e) {
            Response::error($e->getMessage());
        }
    }

    // PUT /api/step/{id}
    public function update($id)
    {
        try {
            $input = json_decode(file_get_contents("php://input"), true);

            $this->service->update($id, $input);

            Response::success();

        } catch (\Throwable $e) {
            Response::error($e->getMessage());
        }
    }

    // DELETE /api/step/{id}
    public function destroy($id)
    {
        try {
            $this->service->delete($id);

            Response::success();

        } catch (\Throwable $e) {
            Response::error($e->getMessage());
        }
    }

    // 批量替换步骤（推荐）
    // POST /api/step/batch
    public function batch()
    {
        try {
            $input = json_decode(file_get_contents("php://input"), true);

            $this->service->replaceSteps(
                intval($input['recipe_id']),
                $input['steps'] ?? []
            );

            Response::success();

        } catch (\Throwable $e) {
            Response::error($e->getMessage());
        }
    }
}