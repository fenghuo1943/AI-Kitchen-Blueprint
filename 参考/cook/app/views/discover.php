<?php

$pageTitle = "发现";
$activeTab = "discover";

include 'layout.php';
?>

<head>
    <meta charset="UTF-8">
    <title>发现 | 菜谱</title>
    <!-- <link rel="stylesheet" href="assets/css/discover.css"> -->
</head>

<body>
    <div class="container">
        <section class="discover-section">
            <div class="section-header">
                <h2>🔥 今日推荐</h2>
            </div>
            <div id="today-grid" class="recipe-grid skeleton-grid"></div>
        </section>
        <section class="discover-section">
            <div class="section-header" style="display: flex; justify-content: flex-start;">
                <h2 style="margin-right: 20px;">🎲 随机推荐</h2>
                <button id="randomBtn" class="btn-normal" style="background: none;">换一批</button>
            </div>
            <div id="random-grid" class="recipe-grid skeleton-grid"></div>
        </section>
        <section class="discover-section">
            <div class="section-header">
                <h2>🆕 最近添加</h2>
            </div>
            <div id="recent-grid" class="recipe-grid skeleton-grid"></div>
        </section>
    </div>
    <script type="module" src="assets/js/discover.js"></script>
    <?php include 'components/recipe_modal.php'; ?>
</body>