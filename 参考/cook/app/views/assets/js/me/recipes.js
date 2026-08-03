import { apiRequest } from '../utils/api.js';
import { setupInfiniteScroll } from '../utils/infiniteScroll.js';

// ===== 我的菜谱 =====
let loadRecipesController = null;
document.addEventListener('DOMContentLoaded', async () => {

    document.getElementById('categorySelect').addEventListener('change', () => loadRecipes(true));
    const debouncedSearch = debounce(() => loadRecipes(true), 800);
    document.getElementById('searchInput').addEventListener('input', debouncedSearch);
    document.getElementById('sortSelect').addEventListener('change', () => loadRecipes(true));
});
function loadRecipes(reset = true) {
    if (!loadRecipesController) initRecipesInfiniteScroll(document.getElementById('recipesList'));
    loadRecipesController.load(true);
    loadCategories();
}
// 加载类别
function loadCategories() {
    const select = document.getElementById('categorySelect');
    apiRequest('api/category?type=recipe')
        /* fetch('api/category?type=recipe')
            .then(r => r.json()) */
        .then(res => {
            if (res.code !== 0) return;
            res.data.forEach(c => {
                const option = document.createElement('option');
                option.value = c.id;
                option.textContent = c.name;
                select.appendChild(option);
            });
        });
}
function initRecipesInfiniteScroll(container) {
    loadRecipesController = setupInfiniteScroll({
        containerOrId: container,                        // DOM 对象，也可以传 id 字符串
        urlBuilder: (page, pageSize) => {
            const category = document.getElementById('categorySelect').value;
            const q = encodeURIComponent(document.getElementById('searchInput').value);
            const sort = document.getElementById('sortSelect').value;
            if (!category && !q) return `api/recipe?page=${page}&pageSize=${pageSize}&sort=${sort}`;

            return `api/recipe?page=${page}&pageSize=${pageSize}&category=${category}&sort=${sort}&q=${q}`;
        },
        renderItem: (recipes, container) => {         // 渲染函数
            const fragment = document.createDocumentFragment();
            recipes.forEach(recipe => {
                const row = document.createElement('div');
                row.className = 'item';

                // 菜谱名称与创建时间
                const nameDiv = document.createElement('div');
                nameDiv.className = 'item-title';
                nameDiv.style.cursor = 'pointer';
                nameDiv.textContent = recipe.title;

                const infoDiv = document.createElement('div');
                infoDiv.className = 'item-meta';
                infoDiv.textContent = `创建于: ${recipe.created_at}`;
                nameDiv.appendChild(infoDiv);
                // 点击打开详情
                nameDiv.addEventListener('click', () => openRecipeModal(recipe.id));
                // 操作按钮
                const actionsDiv = document.createElement('div');
                actionsDiv.className = 'item-actions';
                const deleteBtn = document.createElement('button');
                deleteBtn.className = 'btn-small btn-cancel';
                deleteBtn.textContent = '删除';
                deleteBtn.addEventListener('click', () => deleteRecipe(recipe.id));
                actionsDiv.appendChild(deleteBtn);
                // 组合行
                row.appendChild(nameDiv);
                row.appendChild(actionsDiv);

                fragment.appendChild(row);
            });
            container.appendChild(fragment);
        },
        pageSize: 20
    });
    // 第一次加载
    loadRecipesController.load(true);
}
// 防抖函数
function debounce(fn, delay = 400) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), delay);
    }
}
function deleteRecipe(id) {
    if (!confirm('确定删除此菜谱吗？')) return;
    apiRequest('api/recipe/' + id, 'DELETE', { id })
        /* fetch(`api/recipe/${id}`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id })
        }).then(r => r.json()) */
        .then(data => {
            if (data.code === 0) {
                loadRecipes(false);
            } else {
                alert(data.msg || '删除失败');
            }
        });
}
// ===== 已删除菜谱 =====
let deletedRecipesController = null;
function loadDeletedRecipes() {
    if (!deletedRecipesController) initDeletedRecipes();
    deletedRecipesController.load(true);
}
function initDeletedRecipes() {
    deletedRecipesController = setupInfiniteScroll({
        containerOrId: 'deletedRecipesList', // 容器ID
        urlBuilder: (page, pageSize) => `api/recipe?deleted=1&page=${page}&pageSize=${pageSize}`, // URL生成函数
        renderItem: (recipes) => { // 渲染函数
            const container = document.getElementById('deletedRecipesList');
            const fragment = document.createDocumentFragment();
            recipes.forEach(recipe => {
                const item = document.createElement('div');
                item.className = 'item';
                const titleDiv = document.createElement('div');
                titleDiv.className = 'item-title';
                titleDiv.textContent = recipe.title;
                const infoDiv = document.createElement('div');
                infoDiv.className = 'item-meta';
                infoDiv.textContent = `删除于: ${recipe.deleted_at}`;
                titleDiv.appendChild(infoDiv);
                titleDiv.addEventListener('click', () => openRecipeModal(recipe.id));

                const actionsDiv = document.createElement('div');
                actionsDiv.className = 'item-actions';
                const restoreBtn = document.createElement('button');
                restoreBtn.className = 'btn-small btn-confirm';
                restoreBtn.textContent = '恢复';
                restoreBtn.addEventListener('click', () => restoreRecipe(recipe.id));
                actionsDiv.appendChild(restoreBtn);
                const deleteBtn = document.createElement('button');
                deleteBtn.className = 'btn-small btn-cancel';
                deleteBtn.textContent = '彻底删除';
                deleteBtn.addEventListener('click', () => deleteRecipeForever(recipe.id));
                actionsDiv.appendChild(deleteBtn);

                item.appendChild(titleDiv);
                item.appendChild(actionsDiv);
                fragment.appendChild(item);
            });
            container.appendChild(fragment);
        },
        pageSize: 20 // 每页数量，可根据需要修改
    });
    deletedRecipesController.load(true);
}
function restoreRecipe(id) {
    if (!confirm('确定恢复此菜谱吗？')) return;
    apiRequest(`api/recipe/${id}/restore`, 'POST', { id })
        /* fetch(`api/recipe/${id}/restore`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id })
        }).then(r => r.json()) */
        .then(data => {
            if (data.code === 0) {
                loadDeletedRecipes();
            } else {
                alert(data.msg || '恢复失败');
            }
        });
}
function deleteRecipeForever(id) {
    if (!confirm('确定要彻底删除吗？')) return;
    apiRequest(`api/recipe/${id}?forever=1`, 'DELETE', { id })
        /* fetch(`api/recipe/${id}?forever=1`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id })
        }).then(r => r.json()) */
        .then(data => {
            if (data.code === 0) {
                loadDeletedRecipes();
            } else {
                alert(data.msg || '彻底删除失败');
            }
        });
}
function htmlEscape(str) {
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

window.loadRecipes = loadRecipes;
window.deleteRecipe = deleteRecipe;
window.loadDeletedRecipes = loadDeletedRecipes;
window.restoreRecipe = restoreRecipe;
window.deleteRecipeForever = deleteRecipeForever;