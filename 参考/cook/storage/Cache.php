<?php

namespace Cook\Utils;

class Cache
{
    private static $instance = null;
    private $cacheDir;
    
    private function __construct()
    {
        $this->cacheDir = dirname(dirname(__FILE__)) . '/../zb_users/cache/cook/';
        if (!is_dir($this->cacheDir)) {
            mkdir($this->cacheDir, 0755, true);
        }
    }
    
    public static function getInstance()
    {
        if (self::$instance === null) {
            self::$instance = new Cache();
        }
        return self::$instance;
    }
    
    public function get($key)
    {
        $file = $this->cacheDir . md5($key) . '.cache';
        if (file_exists($file)) {
            $data = unserialize(file_get_contents($file));
            if ($data['expire'] > time()) {
                return $data['value'];
            } else {
                unlink($file);
            }
        }
        return false;
    }
    
    public function set($key, $value, $ttl = 3600)
    {
        $file = $this->cacheDir . md5($key) . '.cache';
        $data = [
            'value' => $value,
            'expire' => time() + $ttl
        ];
        file_put_contents($file, serialize($data));
    }
    
    public function delete($key)
    {
        $file = $this->cacheDir . md5($key) . '.cache';
        if (file_exists($file)) {
            unlink($file);
        }
    }
    
    public function clear()
    {
        $files = glob($this->cacheDir . '*.cache');
        foreach ($files as $file) {
            unlink($file);
        }
    }
}