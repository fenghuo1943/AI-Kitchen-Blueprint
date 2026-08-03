<?php
namespace App\Services;

use App\Repositories\CategoryRepository;

class CategoryService
{
    private $repo;

    public function __construct()
    {
        $this->repo = new CategoryRepository();
    }

    public function getAll($type)
    {
        return $this->repo->getAll($type);
    }

    public function create($type, $name)
    {
        return $this->repo->insert($type, $name);
    }

    public function update($type, $id, $name)
    {
        $this->repo->update($type, $id, $name);
    }

    public function delete($type, $id)
    {
        $this->repo->delete($type, $id);
    }
}