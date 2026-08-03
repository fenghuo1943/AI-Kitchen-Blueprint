<?php
// unified_recipe.php
$pageTitle = "菜谱库";
$activeTab = "cook";

include 'layout.php';
?>


<div class="container">

    <!-- 顶部搜索 -->
    <div class="top-bar">
        <input type="text" id="searchInput" placeholder="搜索菜谱..." class="search-input" autocomplete="off">
        <button id="clearFiltersBtn" class="btn-confirm btn-normal">清除筛选</button>
    </div>

    <div class="filter" id="filtersPanel">
        <!-- 食材筛选 -->
        <div class="filter-row">
            <div class="filter-item">
                <button id="ingFilterBtn" class="btn-confirm btn-normal">食材筛选</button>
            </div>
            
            <!-- 匹配模式 -->
            <div class="filter-item">
                <!-- <label>匹配</label> -->
                <div class="match-mode-switch">
                    <div class="match-mode-option active" data-mode="exact">
                        精确
                    </div>
                    <div class="match-mode-option" data-mode="fuzzy">
                        模糊
                    </div>
                </div>
            </div>
        </div>
        <div id="ingredientsList" class="selectModal-list hide"></div>
        <!-- 第二行筛选 -->

        <div class="filter-row">
            <!-- 排序 -->
            <div class="filter-item">
                <!-- <label>排序</label> -->
                <select id="sortSelect">
                    <option value="score">综合推荐</option>
                    <option value="date">最新添加</option>
                    <option value="cook">做过次数</option>
                    <option value="random">随机推荐</option>
                    <option value="title">名称排序</option>
                </select>
            </div>
            <!-- 类别 -->
            <div class="filter-item">
                <!-- <label>类别</label> -->
                <select id="categorySelect">
                    <option value="">全部</option>
                </select>
            </div>
            <!-- 总数 -->
        <span id="recipeCount" class="filter-count"></span>

        </div>


    </div>
    <div style="border-top: 2px solid #eee;margin-bottom:10px"></div>
    <!-- 菜谱结果 -->
    <div id="list-recipe" class="list-recipe">
        <div class="empty-msg">加载中</div>
    </div>

    <!-- 添加菜谱按钮 -->
    <button id="addBtn" class="fab" onclick="location.href='/cook/add'">＋</button>
</div>

<script type="module" src="assets/js/home.js"></script>
<?php include 'components/recipe_modal.php'; ?>