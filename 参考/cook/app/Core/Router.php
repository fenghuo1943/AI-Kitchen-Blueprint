<?php
namespace App\Core;

class Router
{
    private $zbp;
    public function __construct($zbp = null)
    {
        $this->zbp = $zbp;
    }
    public function dispatch(string $route)
    {
        $route = trim($route, '/');
        $segments = explode('/', $route);

        if ($segments[0] === 'api') {
            $this->dispatchApi($segments);
        } else {
            $this->dispatchWeb($segments);
        }
    }
    /*
    |--------------------------------------------------------------------------
    | API 路由分发
    |--------------------------------------------------------------------------
    */
    private function dispatchApi(array $segments)
    {
        $resource = $segments[1] ?? null;

        if (!$resource) {
            Response::error('API resource missing');
            return;
        }
        $controllerName = ucfirst($resource) . 'Controller';
        $controllerClass = "App\\Controllers\\Api\\{$controllerName}";
        $controllerFile = __DIR__ . "/../Controllers/Api/{$controllerName}.php";

        if (!file_exists($controllerFile)) {
            Response::error('API controller not found');
            return;
        }
        require_once $controllerFile;
        if (!class_exists($controllerClass)) {
            Response::error('API controller class missing');
            return;
        }
        $controller = new $controllerClass($this->zbp);
        $method = $_SERVER['REQUEST_METHOD'];
        $id = $segments[2] ?? null;
        if (!$id && isset($_GET['id'])) {
        $id = $_GET['id'];
    }
        $action = $this->resolveRestAction($method, $id, $_SERVER['REQUEST_URI']);
        if (!method_exists($controller, $action)) {
            Response::error("Method {$action} not allowed");
            return;
        }
        $id ? $controller->$action((int)$id)
            : $controller->$action();
    }
    /*
    |--------------------------------------------------------------------------
    | Web 路由分发
    |--------------------------------------------------------------------------
    */
    private function dispatchWeb(array $segments)
    {
        $controllerName = ucfirst($segments[0] ?? 'home') . 'Controller';
        $method = $segments[1] ?? 'index';
        $param = $segments[2] ?? null;
        $controllerFile = __DIR__ . "/../Controllers/Web/{$controllerName}.php";

        if (!file_exists($controllerFile)) {
            die('Web controller not found');
        }
        require_once $controllerFile;
        if (!class_exists($controllerName)) {
            die('Web controller class missing');
        }
        $controller = new $controllerName($this->zbp);
        if (!method_exists($controller, $method)) {
            die('Web method not found');
        }
        $controller->$method($param);
    }

    /*
    |--------------------------------------------------------------------------
    | REST 方法自动映射
    |--------------------------------------------------------------------------
    */
    private function resolveRestAction(string $httpMethod, $id, string $path = ''): string
    {
        return match ($httpMethod) {
            'GET'    => $id ? 'show' : 'index',
            'POST'   => str_ends_with($path, '/restore') ? 'restore' : 'store',
            'PUT'    => 'update',
            'DELETE' => str_contains($path, '?forever=1') ? 'destroyForever' : 'destroy',
            default  => 'index'
        };
    }
}