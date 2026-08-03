<?php

class PageController
{
    private function render($view, $data = [])
    {
        extract($data);
        require __DIR__ . '/../../views/' . $view . '.php';
    }

    public function home()
    {
        $this->render('home');
    }

    public function library()
    {
        $recipes = [
            ['id' => 1, 'name' => '红烧肉'],
            ['id' => 2, 'name' => '番茄炒蛋']
        ];

        $this->render('library', compact('recipes'));
    }

    public function view($id)
    {
        if (!$id) {
            $this->notFound();
            return;
        }

        $recipe = [
            'id' => $id,
            'name' => '示例菜谱 #' . $id,
            'content' => '这里是菜谱内容...'
        ];

        $this->render('view', compact('recipe'));
    }

    public function notFound()
    {
        http_response_code(404);
        $this->render('404');
    }
}