<?php

ini_set('display_errors', 1);
error_reporting(E_ALL);
require __DIR__ . '/app/Autoload.php';

use App\Core\Router;
require dirname(__FILE__) . '/../zb_system/function/c_system_base.php';
$zbp->Load();

$route = $_GET['route'] ?? 'home/index';

$router = new Router($zbp);
$router->dispatch($route);

