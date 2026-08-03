<?php
namespace App\Services;

use App\Repositories\FavoriteRepository;

class FavoriteService
{
    private $repo;

    public function __construct()
    {
        $this->repo = new FavoriteRepository();
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

    public function add($userId, $recipeId)
    {
        if (!$recipeId) {
            throw new \Exception("recipe_id 不能为空");
        }

        $this->repo->insertIgnore($userId, $recipeId);
    }

    public function remove($userId, $recipeId)
    {
        $this->repo->delete($userId, $recipeId);
    }
}