<?php
//add.php - 菜谱添加页面
/* if (!$zbp->user->ID) {
    $current = $_SERVER['REQUEST_URI'];
    header('Location: /zb_system/cmd.php?act=login&redirect=' . $current);
    exit;
}
 */
include 'layout.php';
?>

<body>
    <div class="page-header" style="padding-left: 10px;padding-right: 10px;">
        <button id="btnBack" class="btn-back">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                <path d="M19 12H6" stroke="#0784ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
                <path d="M12 19L5 12L12 5" stroke="#0784ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
            <span class="sr-only">返回</span>
        </button>
        <h2 id="formTitle">添加菜谱</h2>
        <button type="submit" class="btn-normal btn-confirm submitRecipe">提交</button>
    </div>
    <form id="recipeForm">
        <h3>基础信息</h3>
        <input id="title" placeholder="菜谱标题" autocomplete="off">
        <textarea id="description" placeholder="简单描述"></textarea>
        <input id="cook_time" type="number" placeholder="做菜时间（分钟）" autocomplete="off">

        <h3>分类</h3>
        <div id="categoriesList" class="selectModal-list"></div>
        <button id="btnCat" type="button" class="btn-small" >+ 选择分类</button>

        <h3>食材</h3>
        <div id="ingredientsList" class="selectModal-list"></div>
        <button id="btnIng" type="button" class="btn-small" >+ 选择食材</button>

        <h3>调料</h3>
        <div id="seasoningsList" class="selectModal-list"></div>
        <button id="btnSea" type="button" class="btn-small" >+ 选择调料</button>

        <h3>步骤</h3>
        <div id="stepsBox" style="display: flex; flex-direction: column; gap:5px;"></div>
        <button id="btnAddStep" type="button" class="btn-small">+ 添加步骤</button>

        <br>
        <button type="submit" class="btn-normal btn-confirm submitRecipe">提交</button>

    </form>

    <script type="module" src="assets/js/add.js"></script>
    

</body>