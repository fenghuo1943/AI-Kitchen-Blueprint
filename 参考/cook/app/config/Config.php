<?php

namespace Cook\Config;

class Config
{
    private static $config = null;
    
    public static function load()
    {
        if (self::$config === null) {
            $configFile = dirname(dirname(__FILE__)) . '/config/config.php';
            if (file_exists($configFile)) {
                self::$config = require $configFile;
            } else {
                self::$config = self::getDefaultConfig();
            }
        }
        return self::$config;
    }
    
    public static function get($key, $default = null)
    {
        $config = self::load();
        return isset($config[$key]) ? $config[$key] : $default;
    }
    
    private static function getDefaultConfig()
    {
        return [
            'app' => [
                'name' => '菜谱管理系统',
                'version' => '1.0.0',
                'debug' => false
            ],
            'database' => [
                'prefix' => 'user_',
                'charset' => 'utf8mb4'
            ],
            'cache' => [
                'enabled' => true,
                'ttl' => 3600,
                'driver' => 'file'
            ],
            'pagination' => [
                'per_page' => 20,
                'max_per_page' => 100
            ],
            'upload' => [
                'max_size' => 5242880, // 5MB
                'allowed_types' => ['jpg', 'jpeg', 'png', 'gif'],
                'path' => '/uploads/recipes/'
            ]
        ];
    }
}