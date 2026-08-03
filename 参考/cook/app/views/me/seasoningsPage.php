<!-- 调料管理页面 -->
<div id="seasoningsPage" class="content-page">
    <div class="page-header">
        <button class="btn-back" onclick="goBack()">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
                 xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                <path d="M19 12H6" stroke="#0784ff" stroke-width="2"
                      stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M12 19L5 12L12 5" stroke="#0784ff" stroke-width="2"
                      stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <span class="sr-only">返回</span>
        </button>
        <h2>调料管理</h2>
    </div>
    <!-- 顶部搜索 -->
    <div class="top-bar">
        <input type="text" id="search_seasoning" placeholder="搜索食材..." class="search-input" autocomplete="off">
        <select id="filter_seasoning_category">
            <option value="">全部</option>
        </select>
    </div>
    <!-- <div class="add-section">
        <input type="text" id="newSeasoningName" placeholder="输入新调料名" autocomplete="off">
        <select id="newSeasoningCategory">
            <option value="">-选择分类-</option>
        </select>
        <button onclick="seasoningManager.add()">添加调料</button>
    </div> -->

    <div class="list-recipe" id="seasoningsList">
        <div class="empty-msg">加载中</div>
    </div>
    <button id="addSea" class="fab" >＋</button>
</div>