import { apiRequest } from '../utils/api.js';
import { setupInfiniteScroll } from '../utils/infiniteScroll.js';

// ===== 收藏列表 =====
let favoriteController = null;

function loadFavorites(reset = true) {

    if (!favoriteController) {
        initFavoriteInfiniteScroll(document.getElementById('favoriteList'));
    }

    favoriteController.load(reset);
}

function initFavoriteInfiniteScroll(container) {

    favoriteController = setupInfiniteScroll({
        containerOrId: container,
        urlBuilder: (page, pageSize) =>
            `api/favorite?page=${page}&pageSize=${pageSize}`,

        renderItem: (items, container) => {

            const fragment = document.createDocumentFragment();

            items.forEach(item => {

                const row = document.createElement('div');
                row.className = 'item';

                // 左侧：菜谱名称
                const nameDiv = document.createElement('div');
                nameDiv.className = 'item-title';
                nameDiv.style.cursor = 'pointer';
                nameDiv.textContent = item.title;

                // 收藏时间
                const infoDiv = document.createElement('div');
                infoDiv.className = 'item-meta';
                infoDiv.textContent = `收藏于: ${item.created_at}`;

                nameDiv.appendChild(infoDiv);

                // 点击打开详情
                nameDiv.addEventListener('click', () => {
                    openRecipeModal(item.recipe_id);
                });

                // 右侧操作
                const actionsDiv = document.createElement('div');
                actionsDiv.className = 'item-actions';

                const deleteBtn = document.createElement('button');
                deleteBtn.className = 'btn-small btn-cancel';
                deleteBtn.textContent = '取消收藏';

                deleteBtn.addEventListener('click', () => {
                    deleteFavorite(item.recipe_id);
                });

                actionsDiv.appendChild(deleteBtn);

                // 组合
                row.appendChild(nameDiv);
                row.appendChild(actionsDiv);

                fragment.appendChild(row);
            });

            container.appendChild(fragment);
        },

        pageSize: 20
    });

    favoriteController.load(true);
}


// ===== 删除收藏 =====
function deleteFavorite(recipeId) {

    if (!confirm('确定取消收藏此菜谱吗？')) return;
    apiRequest(`api/favorite/${recipeId}`, 'DELETE')
    /* fetch(`api/favorite/${recipeId}`, {
        method: 'DELETE'
    })
        .then(r => r.json()) */
        .then(data => {

            if (data.code === 0) {

                loadFavorites(true);

            } else {

                alert(data.msg || '取消收藏失败');

            }

        });
}


// ===== 清空收藏 =====
function clearFavorites() {

    if (!confirm('确定清空所有收藏吗？')) return;
    apiRequest(`api/favorite/clear`, 'DELETE')
    /* fetch(`api/favorite/clear`, {
        method: 'DELETE'
    })
        .then(r => r.json()) */
        .then(data => {

            if (data.code === 0) {

                const container = document.getElementById('favoriteList');
                container.innerHTML = '';

                loadFavorites(true);

            } else {

                alert(data.msg || '清空失败');

            }

        });
}

window.loadFavorites = loadFavorites;
window.deleteFavorite = deleteFavorite;
window.clearFavorites = clearFavorites;