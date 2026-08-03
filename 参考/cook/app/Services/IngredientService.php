<?php

namespace App\Services;

use App\Repositories\IngredientRepository;

class IngredientService {
    private $repo;

    public function __construct() {
        $this->repo = new IngredientRepository();
    }

    public function getIngredients() {
        $list = $this->repo->getAll();

        // 以后这里可以加缓存 / 数据加工

        return $list;
    }
    public function create($name, $categoryId) {
        return $this->repo->insert($name, $categoryId);
    }
    public function update($id, $name, $categoryId) {
        return $this->repo->update($id, $name, $categoryId);
    }
    public function delete($id) {
        $this->repo->delete($id);
    }
}
