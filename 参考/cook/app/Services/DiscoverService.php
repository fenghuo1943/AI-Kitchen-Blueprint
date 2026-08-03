<?php
namespace App\Services;

use App\Repositories\DiscoverRepository;

class DiscoverService
{
    private $repo;

    public function __construct()
    {
        $this->repo = new DiscoverRepository();
    }

    public function getTodayRecommend($userId, $limit = 6)
    {
        return $this->repo->findTodayRecommend($userId, $limit);
    }
    public function getHotRecipes($userId, $limit = 6)
    {
        return $this->repo->findHotRecipes($userId, $limit);
    }
    public function getNewRecipes($userId, $limit = 6)
    {
        return $this->repo->findNewRecipes($userId, $limit);
    }
    public function getRandomRecipes($userId, $limit = 6)
    {
        return $this->repo->findRandomRecipes($userId, $limit);
    }
}