<?php

namespace App\Services;

use App\Repositories\SeasoningRepository;

class SeasoningService {
    private $repo;

    public function __construct() {
        $this->repo = new SeasoningRepository();
    }

    public function getList($categoryId = null) {
        return $this->repo->getAll($categoryId);
    }

    public function create($name, $categoryId) {
        return $this->repo->insert(trim($name), $categoryId);
    }

    public function update($id, $name, $categoryId) {
        $this->repo->update(intval($id), trim($name), $categoryId);
    }

    public function delete($id) {
        $this->repo->delete(intval($id));
    }
}
