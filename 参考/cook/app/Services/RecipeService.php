<?php

namespace App\Services;

use App\Repositories\RecipeRepository;
use App\Repositories\RecipeSearchRepository;
use App\Repositories\IngredientRepository;
use App\Repositories\RecipeIngredientRepository;
use App\Repositories\SeasoningRepository;
use App\Repositories\RecipeSeasoningRepository;
use App\Repositories\CategoryRepository;
use App\Repositories\RecipeCategoryRepository;
use App\Repositories\RecipeStepRepository;
use App\Repositories\FavoriteRepository;
use App\Repositories\MenuRepository;
use App\Core\Database;

class RecipeService {
    private RecipeRepository $recipeRepo;
    private RecipeSearchRepository $searchRepo;
    private IngredientRepository $ingredientRepo;
    private RecipeIngredientRepository $recipeIngredientRepo;
    private SeasoningRepository $seasoningRepo;
    private RecipeSeasoningRepository $recipeSeasoningRepo;
    private CategoryRepository $categoryRepo;
    private RecipeCategoryRepository $recipeCategoryRepo;
    private RecipeStepRepository $stepRepo;
    private FavoriteRepository $favoriteRepo;
    private MenuRepository $menuRepo;
    private $db;
    public function __construct() {
        $this->recipeRepo = new RecipeRepository();
        $this->searchRepo = new RecipeSearchRepository();
        $this->ingredientRepo = new IngredientRepository();
        $this->recipeIngredientRepo = new RecipeIngredientRepository();
        $this->seasoningRepo = new SeasoningRepository();
        $this->recipeSeasoningRepo = new RecipeSeasoningRepository();
        $this->categoryRepo = new CategoryRepository();
        $this->recipeCategoryRepo = new RecipeCategoryRepository();
        $this->stepRepo = new RecipeStepRepository();
        $this->favoriteRepo = new FavoriteRepository();
        $this->menuRepo = new MenuRepository();
        $this->db = Database::getInstance();
    }

    public function searchRecipes(int $userId, $ingredients, $category, $matchMode, $keyword, $page, $pageSize, string $sort, string $order, $deleted = false) {
        $page = max(1, intval($page));
        $pageSize = min(50, max(1, intval($pageSize)));
        $offset = ($page - 1) * $pageSize;
        $params = compact(
            'userId',
            'ingredients',
            'category',
            'matchMode',
            'keyword',
            'offset',
            'pageSize',
            'sort',
            'order',
            'deleted'
        );
        $result = $this->searchRepo->search($params);

        $totalPage = ceil($result['total'] / $pageSize);

        return [
            'list' => $result['list'],
            'page' => $page,
            'pageSize' => $pageSize,
            'total' => $result['total'],
            'totalPage' => $totalPage,
            'hasMore' => $page < $totalPage
        ];
    }
    /**保存菜谱（新增或更新）**/
    public function saveRecipe(array $data, int $userId, ?int $recipeId = null): int {
        if (empty($data['title'])) {
            throw new \InvalidArgumentException("标题不能为空");
        }
        $data['cook_time'] = $data['cook_time'] === ''
            ? null
            : (int)$data['cook_time'];
        $pdo = $this->db->getConnection();
        $pdo->beginTransaction();

        try {
            if ($recipeId) {
                $this->recipeRepo->update($recipeId, $data);
                // 删除旧关系
                $this->recipeIngredientRepo->deleteByRecipe($recipeId);
                $this->recipeSeasoningRepo->deleteByRecipe($recipeId);
                $this->recipeCategoryRepo->deleteByRecipe($recipeId);
                $this->stepRepo->deleteByRecipe($recipeId);
            } else {
                $data['user_id'] = $userId;
                $recipeId = $this->recipeRepo->insert($data);
            }
            // 插入食材关系
            foreach ($data['ingredients'] ?? [] as $item) {
                $ingredientId = (int)($item['id'] ?? 0);
                $quantity     = trim($item['quantity'] ?? '');
                if ($ingredientId <= 0) {
                    continue;
                }
                $this->recipeIngredientRepo->insert(
                    $recipeId,
                    $ingredientId,
                    $quantity
                );
            }
            // 插入调料关系
            foreach ($data['seasonings'] ?? [] as $item) {
                $seasoningId = (int)($item['id'] ?? 0);
                $quantity    = trim($item['quantity'] ?? '');
                if ($seasoningId <= 0) {
                    continue;
                }
                $this->recipeSeasoningRepo->insert(
                    $recipeId,
                    $seasoningId,
                    $quantity
                );
            }
            // 插入分类关系
            if (!empty($data['category_ids'])) {
                foreach ($data['category_ids'] as $catId) {
                    $this->recipeCategoryRepo->insert($recipeId, (int)$catId);
                }
            } else {
                $this->recipeCategoryRepo->insert($recipeId, 1);
            }
            // 插入步骤
            $order = 1;
            foreach ($data['steps'] ?? [] as $step) {
                $step = trim($step);
                if ($step !== '') {
                    $this->stepRepo->insert($recipeId, $order++, $step);
                }
            }
            $pdo->commit();
            return $recipeId;
        } catch (\Throwable $e) {
            $pdo->rollBack();
            throw $e;
        }
    }
    public function softDelete($id) {
        $this->recipeRepo->softDelete($id);
    }
    public function delete($id) {
        $this->recipeRepo->delete($id);
    }
    public function restore($id) {
        $this->recipeRepo->restore($id);
    }
    /**
     * 获取单个菜谱完整信息，包括分类、食材、步骤
     */
    public function getRecipeById($userId, $id) {
        $recipe['recipe'] = $this->recipeRepo->findById($id);
        //echo $recipe;
        if (!$recipe['recipe']) {
            return null;
        }
        $recipe['ingredients'] = $this->ingredientRepo->findByRecipe($id);
        $recipe['seasonings']  = $this->seasoningRepo->findByRecipe($id);
        $recipe['categories']  = $this->categoryRepo->findByRecipe($id);
        $recipe['steps']       = $this->stepRepo->findByRecipe($id);
        $recipe['is_favorite'] = $this->isFavorite($userId, $id);
        $recipe['user_logged_in'] = $userId > 0;
        $recipe['is_in_today_menu'] = $this->menuRepo->existsInDate($userId, $id);
        return $recipe;
    }
    


    public function isFavorite($userId, $recipeId) {
        return $this->favoriteRepo->isFavorite($userId, $recipeId);
    }
}
