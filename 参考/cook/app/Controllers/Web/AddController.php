<?php

class AddController
{
    private $zbp;
    public function __construct($zbp) {
        $this->zbp = $zbp;
    }
    private function render($view, $data = [])
    {
        $zbp = $this->zbp;  // 显式传入
        
        extract($data);
        require __DIR__ . '/../../views/add.php';
    }
    public function index()
    {
        $this->render('add');
    }
}