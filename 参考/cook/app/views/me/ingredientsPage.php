<!-- 食材管理页面 -->
<div id="ingredientsPage" class="content-page">
    <div class="page-header">
        <button class="btn-back" onclick="goBack()">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                <path d="M19 12H6" stroke="#0784ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
                <path d="M12 19L5 12L12 5" stroke="#0784ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
            <span class="sr-only">返回</span>
        </button>
        <h2>食材管理</h2>
    </div>
    <!-- 顶部搜索 -->
    <div class="top-bar">
        <input type="text" id="search_ingredient" placeholder="搜索食材..." class="search-input" autocomplete="off">
        <select id="filter_ingredient_category">
            <option value="">全部</option>
        </select>
    </div>
    <!-- <div class="add-section">
        <input type="text" id="newIngName" placeholder="输入新食材名" autocomplete="off">
        <select id="newIngCategory">
            <option value="">-选择分类-</option>
        </select>
        <button onclick="ingredientManager.add()">添加食材</button>
    </div> -->
    <div class="list-recipe"  id="ingredientsList">
        <div class="empty-msg">加载中</div>
    </div>
    <button id="addIng" class="fab" >＋</button>
</div>