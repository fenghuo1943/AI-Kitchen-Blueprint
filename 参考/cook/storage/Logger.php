<?php

namespace Cook\Utils;

class Logger
{
    private static $instance = null;
    private $logFile;
    
    private function __construct()
    {
        $this->logFile = dirname(dirname(__FILE__)) . '/../zb_users/logs/cook_' . date('Y-m') . '.log';
    }
    
    public static function getInstance()
    {
        if (self::$instance === null) {
            self::$instance = new Logger();
        }
        return self::$instance;
    }
    
    public function log($level, $message, $context = [])
    {
        $timestamp = date('Y-m-d H:i:s');
        $contextStr = !empty($context) ? ' ' . json_encode($context, JSON_UNESCAPED_UNICODE) : '';
        $logEntry = "[{$timestamp}] {$level}: {$message}{$contextStr}" . PHP_EOL;
        
        error_log($logEntry, 3, $this->logFile);
    }
    
    public function info($message, $context = [])
    {
        $this->log('INFO', $message, $context);
    }
    
    public function error($message, $context = [])
    {
        $this->log('ERROR', $message, $context);
    }
    
    public function warning($message, $context = [])
    {
        $this->log('WARNING', $message, $context);
    }
}

// 全局异常处理器
set_exception_handler(function($exception) {
    $logger = Logger::getInstance();
    $logger->error('未捕获异常: ' . $exception->getMessage(), [
        'file' => $exception->getFile(),
        'line' => $exception->getLine(),
        'trace' => $exception->getTraceAsString()
    ]);
    
    // 在生产环境中不显示详细错误信息
    if (defined('DEBUG') && DEBUG) {
        echo "致命错误: " . $exception->getMessage();
    } else {
        echo "系统发生错误，请联系管理员";
    }
});