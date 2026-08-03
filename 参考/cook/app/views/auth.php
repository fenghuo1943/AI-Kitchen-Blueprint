<?php
// login_register.php
?>
<!DOCTYPE html>
<html lang="zh-CN">

<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>菜谱网站登录/注册</title>
  <style>
    /* 基础样式 */
    body {
      font-family: "Microsoft YaHei", sans-serif;
      background-color: #fff7ed;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      margin: 0;
    }

    .container {
      background-color: #fff;
      width: 380px;
      border-radius: 20px;
      box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
      padding: 40px 30px;
      box-sizing: border-box;
      position: relative;
    }

    h1 {
      text-align: center;
      color: #b45309;
      margin-bottom: 30px;
    }

    .tab-buttons {
      display: flex;
      justify-content: center;
      margin-bottom: 30px;
    }

    .tab-buttons button {
      flex: 1;
      padding: 10px;
      font-weight: bold;
      border: none;
      background: none;
      cursor: pointer;
      color: #888;
      border-bottom: 2px solid transparent;
      transition: all 0.3s;
    }

    .tab-buttons button.active {
      color: #b45309;
      border-bottom: 2px solid #b45309;
    }

    form {
      display: none;
      flex-direction: column;
    }

    form.active {
      display: flex;
    }

    input[type="text"],
    input[type="email"],
    input[type="password"] {
      padding: 10px;
      margin-top: 8px;
      margin-bottom: 15px;
      border: 1px solid #ccc;
      border-radius: 10px;
      outline: none;
      font-size: 14px;
    }

    input[type="text"]:focus,
    input[type="email"]:focus,
    input[type="password"]:focus {
      border-color: #f59e0b;
    }

    button.submit-btn {
      padding: 10px;
      background-color: #f59e0b;
      color: #fff;
      border: none;
      border-radius: 10px;
      cursor: pointer;
      font-size: 16px;
      display: flex;
      justify-content: center;
      align-items: center;
      transition: background 0.3s;
    }

    button.submit-btn:hover {
      background-color: #d97706;
    }

    .spinner {
      display: none;
      margin-left: 8px;
      border: 3px solid #fff;
      border-top: 3px solid #fbbf24;
      border-radius: 50%;
      width: 18px;
      height: 18px;
      animation: spin 1s linear infinite;
    }

    @keyframes spin {
      0% {
        transform: rotate(0deg);
      }

      100% {
        transform: rotate(360deg);
      }
    }

    .msg {
      text-align: center;
      margin-bottom: 10px;
      font-size: 14px;
    }

    .msg.error {
      color: red;
    }

    .msg.success {
      color: green;
    }
  </style>
</head>

<body>

  <div class="container">
    <h1>菜谱网站</h1>
    <div class="tab-buttons">
      <button id="loginTab" class="active">登录</button>
      <button id="registerTab">注册</button>
    </div>

    <!-- 登录表单 -->
    <form id="loginForm" class="active">
      <div id="loginMsg" class="msg error"></div>
      <label>用户名或邮箱</label>
      <input id="loginUsername" type="text" required placeholder="请输入用户名或邮箱">
      <label>密码</label>
      <input id="loginPassword" type="password" required placeholder="请输入密码">
      <button type="submit" class="submit-btn">
        <span id="loginBtnText">登录</span>
        <div class="spinner" id="loginSpinner"></div>
      </button>
    </form>

    <!-- 注册表单 -->
    <form id="registerForm">
      <div id="registerMsg" class="msg error"></div>
      <label>用户名</label>
      <input id="regUsername" type="text" required placeholder="请输入用户名">
      <label>邮箱</label>
      <input id="regEmail" type="email" required placeholder="请输入邮箱">
      <label>密码</label>
      <input id="regPassword" type="password" required placeholder="请输入密码">
      <button type="submit" class="submit-btn">
        <span id="regBtnText">注册</span>
        <div class="spinner" id="regSpinner"></div>
      </button>
    </form>
  </div>

  <script src="assets/js/auth.js"></script>

</body>

</html>