<!-- 我的菜谱页面 -->
<div id="recipesPage" class="content-page">
    <div class="page-header">
        <button class="btn-back" onclick="goBack()">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                <path d="M19 12H6" stroke="#0784ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
                <path d="M12 19L5 12L12 5" stroke="#0784ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
            <span class="sr-only">返回</span>
        </button>
        <h2>菜谱管理</h2>
    </div>
    <div class="filter" style="margin-bottom:10px">
        <div class="filter-item">
            <input type="text" id="searchInput" placeholder="搜索菜谱..." class="search-input" autocomplete="off">
            <select id="categorySelect">
                <option value="">全部</option>
            </select>
            <!-- 排序 -->
            <div class="filter-item">
                <!-- <label>排序</label> -->
                <select id="sortSelect">
                    <option value="date">最新添加</option>
                    <option value="title">名称排序</option>
                    <option value="score">综合推荐</option>
                    <option value="cook">做过次数</option>
                    <option value="random">随机推荐</option>
                </select>
            </div>
        </div>
    </div>
    <div class="list-recipe" id="recipesList">
        <div class="empty-msg">加载中</div>
    </div>

    <!-- 修改添加菜谱按钮样式，与library.php保持一致 -->
    <button id="addBtn" class="fab" onclick="location.href='/cook/add?from=me'">＋</button>
</div>