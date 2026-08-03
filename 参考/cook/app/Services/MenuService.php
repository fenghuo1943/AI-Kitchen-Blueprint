<?php

namespace App\Services;

use App\Repositories\MenuRepository;
use App\Core\Response;

class MenuService {
    private MenuRepository $repo;

    public function __construct() {
        $this->repo = new MenuRepository();
    }

    /**
     * 添加到某天菜单
     */
    public function add(int $userId, int $recipeId, string $date): void {
        if (!$date) {
            throw new \InvalidArgumentException("日期不能为空");
        }

        if ($this->repo->exists($userId, $recipeId, $date)) {
            throw new \Exception($date."已存在该菜谱");
        }
        $this->repo->addRecipe($userId, $recipeId, $date);
    }

    /**
     * 删除
     */
    public function remove(int $userId, int $recipeId, string $date): void {
        $this->repo->removeRecipe($userId, $recipeId, $date);
    }

    /**
     * 获取某天菜单
     */
    public function getByDate(int $userId, string $date): array {
        $list= $this->repo->getByDate($userId, $date);
        return $this->repo->getByDate($userId, $date);
    }
    /**
     * 获取某天菜单中的所有食材
     */
    public function getIngredientsByDate(int $userId, string $date): array {
        return $this->repo->getIngredientsByDate($userId, $date);
    }
    /**
     * 获取某天菜单中的所有调料
     */
    public function getSeasoningsByDate(int $userId, string $date): array {
        return $this->repo->getSeasoningsByDate($userId, $date);
    }
    /**
     * 获取某月有菜单的日期
     */
    public function getMonthDates(int $userId, string $month): array {
        $rows = $this->repo->getDatesByMonth($userId, $month);

        return array_map(fn($r) => $r['target_date'], $rows);
    }
    /**
     * 获取瀑布流结构
     */
    public function getWaterfall(int $userId,int $page, int $pageSize): array {
        //$rows = $this->repo->getAllByUser($userId);
        $rows = $this->repo->getByUserWithPage($userId,$page,$pageSize);
        $grouped = [];

        foreach ($rows['list'] as $row) {
            $date = $row['target_date'];

            if (!isset($grouped[$date])) {
                $grouped[$date] = [
                    'date' => $date,
                    'recipes' => []
                ];
            }

            $grouped[$date]['recipes'][] = [
                'id' => $row['id'],
                'title' => $row['title'],
                'cover' => $row['cover'],
                'cook_time' => $row['cook_time'],
            ];
        }

        return [
            'list' => array_values($grouped),
            'totalPage' => $rows['totalPage']
        ];
    }
    
}
