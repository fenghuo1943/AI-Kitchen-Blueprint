<?php
// menu.php
$pageTitle = "菜单";
$activeTab = "menu";

include 'layout.php';
?>

<div class="menu-mode-switch">
    <button class="mode-btn active" data-mode="single">按日期查看</button>
    <button class="mode-btn" data-mode="waterfall">瀑布流</button>
</div>

<!-- 单日模式 -->
<div id="single-mode" class="container">
    <div id="calendar"></div>
    <div id="menu-list-ingredients" class="selectModal-list" style="margin-bottom: 10px;">
    </div>
    <div id="menu-list-seasonings" class="selectModal-list" style="margin-bottom: 10px;">
    </div>
    <div id="list-menu" class="list-recipe">
        <div class="empty-msg">加载中</div>
    </div>
</div>

<!-- 瀑布流模式 -->
<div id="waterfall-mode" class="container" style="display:none;">
    <div id="waterfall-list">
        <div class="empty-msg">加载中</div>
    </div>
</div>

<script type="module" src="assets/js/menu.js"></script>

<?php include 'components/recipe_modal.php'; ?>