<!-- 食材分类管理页面 -->
<div id="ingCategoriesPage" class="content-page">
    <div class="page-header">
        <button class="btn-back" onclick="goBack()">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                <path d="M19 12H6" stroke="#0784ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
                <path d="M12 19L5 12L12 5" stroke="#0784ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
            <span class="sr-only">返回</span>
        </button>
        <h2>食材分类管理</h2>
    </div>
    <div class="add-section">
        <input type="text" id="newIngCatName" placeholder="输入新食材分类名" autocomplete="off">
        <button id="addIng_category" >添加分类</button>
    </div>
    <div class="list-recipe" id="ingCategoriesList">
        <div class="empty-msg">加载中</div>
    </div>
    <button id="addIng_category" class="fab" >＋</button>
</div>