<?php
namespace App\Core;
class Cache
{
    public static function short()
    {
        header('Cache-Control: public, max-age=30');
    }

    public static function medium()
    {
        header('Cache-Control: public, max-age=300');
    }

    public static function long()
    {
        header('Cache-Control: public, max-age=3600');
    }
}