<?php

class RecipeController
{
    private $zbp;
    public function __construct($zbp) {
        $this->zbp = $zbp;
    }
    private function render($view, $data = [])
    {
        $zbp = $this->zbp;  // 显式传入
        
        extract($data);
        require __DIR__ . '/../../views/recipe.php';
    }
    public function index()
    {
        $this->render('recipe');
    }
}