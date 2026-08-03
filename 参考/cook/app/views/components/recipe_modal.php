<?php
// recipe_modal.php
// 菜谱详情弹窗组件
// 使用方法: include 'components/recipe_modal.php';

// 初始化收藏状态变量
$is_favorite = false;

// 如果用户已登录，检查是否已收藏该菜谱
//if ($zbp->user->ID) {
    //$uid = $zbp->user->ID;
    $uid = 1; // 临时使用固定用户ID，实际应用中应使用登录用户ID
    $recipe_id = isset($_GET['id']) ? intval($_GET['id']) : 0;

    if ($recipe_id > 0) {
        $sql = "
        SELECT id FROM user_favorites
        WHERE user_id = $uid
        AND recipe_id = $recipe_id
        LIMIT 1
        ";

        $check = $zbp->db->Query($sql);

        if ($check) {
            $is_favorite = true;
        }
    }
//}
?>
<!-- 菜谱详情模态框 -->
<div id="recipeModal" class="recipe-modal-overlay">
    <div class="recipe-modal-content">
        
        <div class="recipe-modal-body" id="recipeModalBody">
            <div class="btn-back" onclick="closeRecipeModal()">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                <path d="M19 12H6" stroke="#0784ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M12 19L5 12L12 5" stroke="#0784ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
        </div>
            <div class="loading">加载中...</div>
        </div>
        <?php include dirname(__FILE__) . '/../layout.php'; ?>
    </div>
</div>


<script type="module" src="assets/js/recipe_modal.js"></script>