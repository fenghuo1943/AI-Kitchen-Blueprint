<?php
namespace App\Core;

class Response {

    public static function success($data = [], $msg = 'ok') {
        echo json_encode([
            'code' => 0,
            'msg'  => $msg,
            'data' => $data
        ]);
        exit;
    }

    public static function error($msg = 'error', $code = 1) {
        echo json_encode([
            'code' => $code,
            'msg'  => $msg,
            'data' => null
        ]);
        exit;
    }
}