<?php
if (!isset($pageTitle)) $pageTitle = "家用菜谱";
if (!isset($activeTab)) $activeTab = "";
?>
<!DOCTYPE html>
<html class="html11">

<head>
    <meta charset="utf-8">
    <title><?php echo $pageTitle; ?></title>
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
    <?php
    if (!isset($GLOBALS['layout_css_loaded'])) {
        $GLOBALS['layout_css_loaded'] = true;
        echo '<link rel="stylesheet" href="assets/css/style.css">';
    }
    ?>
</head>
<?php if (!isset($GLOBALS['global_js_loaded'])) {
    $GLOBALS['global_js_loaded'] = true;
    echo '<script type="module" src="assets/js/utils/api.js"></script>';
    echo '<script type="module" src="assets/js/utils/toast.js"></script>';
    echo '<script type="module" src="assets/js/utils/user.js"></script>';
  }?>
<body>

    <div class="container">
    </div>
    <div class="tabbar">
        <a href="/cook/home" class="<?php echo $activeTab == 'cook' ? 'active' : ''; ?>">
            <span class="icon">🍳</span>
            做菜
        </a>
        <a href="/cook/menu" class="<?php echo $activeTab == 'menu' ? 'active' : ''; ?>">
            <span class="icon">📚</span>
            菜单
        </a>
        <a href="/cook/discover" class="<?php echo $activeTab == 'discover' ? 'active' : ''; ?>">
            <span class="icon">✨</span>
            发现
        </a>
        <a href="/cook/me" class="<?php echo $activeTab == 'me' ? 'active' : ''; ?>">
            <span class="icon">👤</span>
            我的
        </a>
    </div>
    <?php if (!isset($GLOBALS['global_modal_js_loaded'])) {
        $GLOBALS['global_modal_js_loaded'] = true;
        include 'components/globalModal.php';
        include 'components/select_modal.php';
    } ?>
</body>

</html>

