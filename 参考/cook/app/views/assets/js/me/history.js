import { apiRequest } from '../utils/api.js';
import { setupInfiniteScroll } from '../utils/infiniteScroll.js';

// ===== 浏览历史 =====
let historyController = null;

function loadHistory(reset = true) {

    if (!historyController) {
        initHistoryInfiniteScroll(document.getElementById('historyList'));
    }
    historyController.load(reset);
}

function initHistoryInfiniteScroll(container) {

    historyController = setupInfiniteScroll({
        containerOrId: container,
        urlBuilder: (page, pageSize) =>
            `api/history?page=${page}&pageSize=${pageSize}`,
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

                // 浏览时间
                const infoDiv = document.createElement('div');
                infoDiv.className = 'item-meta';
                infoDiv.textContent = `浏览于: ${item.viewed_at}`;

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
                deleteBtn.textContent = '删除记录';

                deleteBtn.addEventListener('click', () => {
                    deleteHistory(item.recipe_id);
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

    historyController.load(true);
}


// ===== 删除单条历史 =====
function deleteHistory(recipeId) {

    if (!confirm('确定删除此浏览记录吗？')) return;
    apiRequest(`api/history/${recipeId}`, 'DELETE')
    /* fetch(`api/history/${recipeId}`, {
        method: 'DELETE'
    })
        .then(r => r.json()) */
        .then(data => {

            if (data.code === 0) {
                loadHistory(true);
            } else {
                alert(data.msg || '删除失败');
            }

        });
}


// ===== 清空历史 =====
function clearHistory() {

    if (!confirm('确定清空所有浏览历史吗？')) return;
    apiRequest('api/history/clear', 'DELETE')
    /* fetch(`api/history/clear`, {
        method: 'DELETE'
    })
        .then(r => r.json()) */
        .then(data => {

            if (data.code === 0) {

                const container = document.getElementById('historyList');
                container.innerHTML = '';

                loadHistory(true);

            } else {
                alert(data.msg || '清空失败');
            }

        });
}

window.loadHistory = loadHistory;
window.deleteHistory = deleteHistory;
window.clearHistory = clearHistory;