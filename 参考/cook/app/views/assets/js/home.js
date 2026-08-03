//unified.js
import { setupInfiniteScroll } from './utils/infiniteScroll.js';
import { toggleFavorite, toggleDateMenu, initAutoHideButton, showAddMenu } from './utils/func.js';
import { apiRequest } from './utils/api.js';

let autoSearchController = null;
let allIngCategories = [];
let allIngredients = [];
let selectedIngredients = {};

// 初始化
document.addEventListener('DOMContentLoaded', async () => {
    const user = await getProfile();
    if (user.code === 0) {
        userId = user.data['id'];
    }
    await loadIngCategories();
    await GetIngredients();
    loadCategories();
    initMatchModeSwitch();
    initAutoSearch();
    initAutoHideButton({ btnId: 'addBtn' });
});
const toggle = document.getElementById('filterToggle');
const panel = document.getElementById('filtersPanel');

// 加载食材
async function loadIngCategories() {
    //const res = await fetch("api/category?type=ingredient");
    const data = await apiRequest('api/category?type=ingredient');
    allIngCategories = data.data || [];
}
async function GetIngredients() {
    //const res = await fetch("api/ingredient");
    const data = await apiRequest('api/ingredient');
    allIngredients = data.data || [];

}
// 加载类别
function loadCategories() {
    const select = document.getElementById('categorySelect');
    //fetch('api/category?type=recipe')
    apiRequest('api/category?type=recipe')
        //.then(r => r.json())
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
function openIngredientModal() {
    let html = '';
    if (allIngCategories && allIngCategories.length > 0) {
        html += `
        <div class="selectModal-row">
            <input id="modalSearch" placeholder="搜索食材" autocomplete="off">
            <select id="ingCategoryFilter" >
                <option value="">全部分类</option>
        `;
        allIngCategories.forEach(c => {
            html += `<option value="${c.id}">${c.name}</option>`;
        });
        html += '</select></div>';
    }
    html += '<div id="modalList" class="selectModal-list"></div>';
    //document.getElementById('ingredientsList').innerHTML = html;
    showModal('食材筛选', html);
    renderIngredientList();
    document.getElementById('modalSearch')?.addEventListener('input', e => {
        filterModalItems(e.target.value, 'ing');
    });
    document.getElementById('ingCategoryFilter')?.addEventListener('change', e => {
        filterModalItemsByCategory(e.target.value);
    });
}
function renderIngredientList() {
    const listContainer = document.getElementById('modalList');
    if (!listContainer) return;

    listContainer.innerHTML = '';
    allIngredients.forEach(ing => {
        let sel = selectedIngredients[ing.id] ? ' selected' : '';
        let safeName = ing.name.replace(/'/g, "\\'");
        const span = document.createElement('span');
        span.className = 'item-modal' + sel;
        span.dataset.id = ing.id;
        span.dataset.type = 'ing';
        span.dataset.categoryId = ing.category_id;
        span.innerText = ing.name;
        span.onclick = () => toggleIngredient(ing.id, safeName, true);
        listContainer.appendChild(span);
    });
}
function toggleIngredient(id, name, isFind = true) {
    if (selectedIngredients[id]) {
        delete selectedIngredients[id];
    } else {
        selectedIngredients[id] = {
            id: id,
            name: name
        };
    }
    if (isFind) {
        loadRecipes(true);
    }
    document.querySelectorAll('.item-modal[data-type="ing"]').forEach(el => {
        if (el.getAttribute('data-id') == id) {
            if (selectedIngredients[id]) el.classList.add('selected');
            else el.classList.remove('selected');
        }
    });
    updateIngredientList(isFind);
}
function updateIngredientList(isFind = true) {
    const box = document.getElementById('ingredientsList');
    if (!box) return;
    box.innerHTML = '';
    for (let id in selectedIngredients) {
        const item = selectedIngredients[id];
        console.log(item);
        const div = document.createElement('div');
        div.className = 'item-chosen';
        const span = document.createElement('span');
        span.textContent = item.name;
        div.appendChild(span);
        const input = document.createElement('input');
        const remove = document.createElement('span');
        remove.textContent = '×';
        remove.onclick = () => {
            delete selectedIngredients[id];
            updateIngredientList();
        };
        div.appendChild(remove);
        box.appendChild(div);
    }
    if (box.children.length === 0)
        box.classList.add('hide');
    else
        box.classList.remove('hide');
    if (isFind) loadRecipes(true);
}
// 匹配模式切换
function initMatchModeSwitch() {
    document.querySelectorAll('.match-mode-option').forEach(el => {
        el.addEventListener('click', () => {
            document.querySelectorAll('.match-mode-option').forEach(o => o.classList.remove('active'));
            el.classList.add('active');
            loadRecipes(true);
        });
    });
}
// 清除筛选
document.getElementById('clearFiltersBtn').addEventListener('click', () => {
    selectedIngredients = {};
    document
        .querySelectorAll('.item-modal[data-type="ing"]')
        .forEach(el => el.classList.remove('selected'));
    updateIngredientList();
    document.getElementById('searchInput').value = '';
    loadRecipes(true);
});
//食材筛选框
document.getElementById('ingFilterBtn').addEventListener('click', () => {
    openIngredientModal();
});

// 搜索与筛选
const debouncedSearch = debounce(() => loadRecipes(true), 800);

document.getElementById('searchInput').addEventListener('input', debouncedSearch);
//document.getElementById('ingredientsList').addEventListener('change', () => loadRecipes(true));

document.getElementById('categorySelect').addEventListener('change', () => loadRecipes(true));
document.getElementById('sortSelect').addEventListener('change', () => loadRecipes(true));


function loadRecipes(reset = true) {
    if (!autoSearchController) initAutoSearch();
    autoSearchController.load(true);
}
// 初始化无限滚动
function initAutoSearch() {
    autoSearchController = setupInfiniteScroll({
        containerOrId: 'list-recipe',
        urlBuilder: (page, pageSize) => {
            const ingredients = Object.keys(selectedIngredients);
            const category = document.getElementById('categorySelect').value;
            const match = document.querySelector('.match-mode-option.active').dataset.mode;
            const q = encodeURIComponent(document.getElementById('searchInput').value);
            const sort = document.getElementById('sortSelect').value;
            if (!ingredients.length && !category && !q) return `api/recipe?page=${page}&pageSize=${pageSize}&sort=${sort}`;

            return `api/recipe?page=${page}&pageSize=${pageSize}&ingredients=${ingredients.join(',')}&category=${category}&match=${match}&sort=${sort}&q=${q}`;
        },
        renderItem: (list, container,total) => {
            if (!list || list.length === 0) return;
            const fragment = document.createDocumentFragment();
            list.forEach(r => {
                const item = document.createElement('div');
                item.className = 'item';
                const titleDiv = document.createElement('div');
                titleDiv.className = 'item-title';
                titleDiv.textContent = r.title;
                const infoDiv = document.createElement('div');
                infoDiv.className = 'item-meta';
                infoDiv.textContent = `${r.cook_time || '未知'} 分钟`;
                titleDiv.appendChild(infoDiv);
                titleDiv.addEventListener('click', () => openRecipeModal(r.id));
                item.appendChild(titleDiv);
                if (userId > 0) {
                    const actionDiv = document.createElement('div');
                    actionDiv.className = 'item-actions';
                    const favoriteBtn = document.createElement('button');
                    favoriteBtn.className = 'btn-small';
                    favoriteBtn.classList.toggle('btn-confirm', !r.is_favorited);
                    favoriteBtn.classList.toggle('btn-cancel', r.is_favorited);
                    favoriteBtn.textContent = `${r.is_favorited ? '取消' : ''}收藏`;
                    favoriteBtn.addEventListener('click', () => favoriteClick(r.id, favoriteBtn));
                    actionDiv.appendChild(favoriteBtn);
                    //加入菜单按钮
                    const addMenuBtn = document.createElement('button');
                    addMenuBtn.className = 'btn-small btn-confirm';
                    //addMenuBtn.classList.toggle('btn-confirm', !r.is_in_today_menu);
                    //addMenuBtn.classList.toggle('btn-cancel', r.is_in_today_menu);
                    addMenuBtn.style.maxWidth = '100px';
                    addMenuBtn.textContent = '加入菜单';
                    //addMenuBtn.textContent = `${r.is_in_today_menu ? '删除' : '加入'}菜单`;
                    addMenuBtn.addEventListener('click', () => todayMenuClick(r.id, addMenuBtn));
                    actionDiv.appendChild(addMenuBtn);
                    item.appendChild(actionDiv);
                }
                fragment.appendChild(item);

            });
            container.appendChild(fragment);
            document.getElementById('recipeCount').textContent =
    `${total}个菜谱`;
        },
        pageSize: 10
    });

    autoSearchController.load(true);
}
// 防抖函数
function debounce(fn, delay = 400) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), delay);
    }
}

//切换收藏
async function favoriteClick(recipeId, btn) {
    const del = btn.innerHTML == '取消收藏';
    try {
        const favorited = await toggleFavorite(recipeId, del);

        btn.innerHTML = favorited ? '取消收藏' : '收藏';
        btn.classList.toggle('btn-confirm', !favorited);
        btn.classList.toggle('btn-cancel', favorited);
        Toast.success(favorited ? '已收藏' : '已取消收藏');

    } catch (e) {
        Toast.error(e.message);
    }
}
//切换菜单
async function todayMenuClick(recipeId, btn) {
    const del = btn.innerHTML == '删除菜单';
    try {
        showAddMenu(recipeId);
        /* const added = await toggleDateMenu(recipeId, del);
        btn.innerHTML = added ? '删除菜单' : '加入菜单';
        btn.classList.toggle('btn-confirm', !added);
        btn.classList.toggle('btn-cancel', added);
        Toast.success(added ? '已加入今日菜单' : '已移除'); */
    } catch (e) {
        Toast.error(e.message);
    }
}

// 页面加载时初始化
window.addEventListener('load', () => {
    const hash = location.hash.slice(1); // 去掉 #
    const params = new URLSearchParams(hash);
    const id = params.get("id") || 0;
    if (id) {
        openRecipeModal(id);
    }
});

function filterModalItemsByCategory(catId) {
    catId = catId ? String(catId) : '';
    document.querySelectorAll('.item-modal[data-type="ing"]').forEach(el => {
        if (!catId) {
            el.style.display = '';
        } else {
            el.style.display = el.getAttribute('data-category-id') == catId ? 'inline-block' : 'none';
        }
    });
}
function filterModalItems(query, type) {
    query = query.trim().toLowerCase();
    document.querySelectorAll('.item-modal[data-type="' + type + '"]').forEach(el => {
        let text = el.textContent.toLowerCase();
        el.style.display = text.indexOf(query) !== -1 ? 'inline-block' : 'none';
    });
}
