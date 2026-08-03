<?php
namespace App\Services;

use App\Repositories\HistoryRepository;

class HistoryService
{
    private $repo;

    public function __construct()
    {
        $this->repo = new HistoryRepository();
    }

    public function getList($userId, $page = 1, $pageSize = 30)
    {
        $page = max(1, intval($page));
        $pageSize = max(1, intval($pageSize));

        $offset = ($page - 1) * $pageSize;
        $list = $this->repo->getByUser($userId, $offset, $pageSize);
        $total = $this->repo->countByUser($userId);
        return [
            'list' => $list,
            'total' => $total
        ];
    }

    // 存在则更新时间，不存在则插入
    public function record($userId, $recipeId)
    {
        if (!$recipeId) {
            throw new \Exception("recipe_id 不能为空");
        }

        $this->repo->upsert($userId, $recipeId);
    }

    public function clear($userId)
    {
        $this->repo->deleteByUser($userId);
    }
}