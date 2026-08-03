<?php
namespace App\Services;

use App\Repositories\StepRepository;

class StepService
{
    private $repo;

    public function __construct()
    {
        $this->repo = new StepRepository();
    }

    public function getByRecipe($recipeId)
    {
        return $this->repo->getByRecipe($recipeId);
    }

    public function create($data)
    {
        if (empty($data['recipe_id']) || empty($data['content'])) {
            throw new \Exception("参数不完整");
        }

        $recipeId  = intval($data['recipe_id']);
        $stepOrder = intval($data['step_order'] ?? 0);

        if ($stepOrder <= 0) {
            throw new \Exception("step_order 必须大于 0");
        }

        return $this->repo->insert(
            $recipeId,
            $stepOrder,
            trim($data['content']),
            $data['image'] ?? null
        );
    }

    public function update($id, $data)
    {
        if (empty($data['content'])) {
            throw new \Exception("步骤内容不能为空");
        }

        $stepOrder = intval($data['step_order'] ?? 0);

        if ($stepOrder <= 0) {
            throw new \Exception("step_order 必须大于 0");
        }

        $this->repo->update(
            intval($id),
            $stepOrder,
            trim($data['content']),
            $data['image'] ?? null
        );
    }

    public function delete($id)
    {
        $this->repo->delete(intval($id));
    }

    /**
     * 推荐编辑菜谱时使用
     * 先删除再重建（避免 UNIQUE 冲突）
     */
    public function replaceSteps($recipeId, $steps)
    {
        if (!$recipeId) {
            throw new \Exception("缺少 recipe_id");
        }

        $this->repo->deleteByRecipe($recipeId);

        $order = 1;

        foreach ($steps as $step) {

            if (empty($step['content'])) {
                continue;
            }

            $this->repo->insert(
                $recipeId,
                $order++,
                trim($step['content']),
                $step['image'] ?? null
            );
        }
    }
}