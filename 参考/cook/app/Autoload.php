<?php

// 缓存文件路径
$autoloadCacheFile = __DIR__ . '/.autoload_cache.php';

// 1. 读取缓存，如果不存在就用空数组
$autoloadCache = file_exists($autoloadCacheFile) ? include $autoloadCacheFile : [];

// 2. 命名空间前缀映射
$mappings = [
    'App\\' => __DIR__ . '/',
    'Overtrue\\Pinyin\\' => __DIR__ . '/plugin/overtrue/pinyin/src/',
    'Firebase\\JWT\\' => __DIR__ . '/plugin/firebase/php-jwt/src/',
];
spl_autoload_register(function ($class) use ($mappings, &$autoloadCache, $autoloadCacheFile) {

     // 如果缓存里有，先检查文件是否存在
     if (isset($autoloadCache[$class])) {
        $cachedFile = $autoloadCache[$class];
        if (file_exists($cachedFile)) {
            require $cachedFile;
            return;
        } else {
            // 文件不存在，删除缓存
            unset($autoloadCache[$class]);
            file_put_contents($autoloadCacheFile, '<?php return ' . var_export($autoloadCache, true) . ';');
        }
    }  

    // 遍历映射寻找类文件
    foreach ($mappings as $prefix => $baseDir) {
        if (str_starts_with($class, $prefix)) {
            
            $relativeClass = substr($class, strlen($prefix));
            $file = $baseDir . str_replace('\\', '/', $relativeClass) . '.php';
            
            
            if (file_exists($file)) {
                // 加载类
                require $file;

                // 更新缓存
                $autoloadCache[$class] = $file;
                file_put_contents($autoloadCacheFile, '<?php return ' . var_export($autoloadCache, true) . ';');

                return;
            }
        }
    }

});