<?php

class HomeController
{
    private $zbp;
    public function __construct($zbp) {
        $this->zbp = $zbp;
    }
    private function render($view, $data = [])
    {
        $zbp = $this->zbp;  // 显式传入
        $selected = isset($_GET['ingredients'])
            ? array_map('intval', $_GET['ingredients'])
            : [];

        $matchMode = $_GET['match_mode'] ?? 'exact';
        extract($data);
        require __DIR__ . '/../../views/home.php';
    }
    public function index()
    {
        $this->render('home');
    }
}?>