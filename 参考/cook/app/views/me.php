<?php

//$pageTitle = "我的";
$activeTab = "me";
/* $user_id = 1;
if (!$zbp->user->ID) {
    $current = $_SERVER['REQUEST_URI'];
    header('Location: /zb_system/cmd.php?act=login&redirect=' . $current);
    exit;
    //$user_id = 1;
} else {
    $user_id = $zbp->user->ID;
} */
?>
<?php include __DIR__ . '/layout.php'; ?>

<div class="profile-header">
    <div class="avatar"></div>
    <h2 id="userName"></h2>
</div>

<?php
// 自动加载 pages 下所有模块
$pagesDir = __DIR__ . '/me/';
foreach (glob($pagesDir . '*.php') as $pageFile) {
    include $pageFile;
}
?>
<?php include 'components/recipe_modal.php'; ?>
<!-- JS -->
<script type="module" src="assets/js/me/menu.js"></script>
<script type="module" src="assets/js/me/recipes.js"></script>
<script type="module" src="assets/js/me/history.js"></script>
<script type="module" src="assets/js/me/favorites.js"></script>
<!-- <script src="assets/js/me/categories.js"></script> -->
<script src="assets/js/me/entityManager.js"></script>
<!-- <script src="assets/js/me/ingredients.js"></script>
<script src="assets/js/me/ingCategories.js"></script>
<script src="assets/js/me/seasonings.js"></script>
<script src="assets/js/me/seasoningCategories.js"></script> -->
<script src="assets/js/me/editModal.js"></script>