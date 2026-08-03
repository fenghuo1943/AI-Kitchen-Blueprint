/* ============================================================
   通用实体管理器
   支持：
   - 实体 CRUD
   - 分类 CRUD
   - 复用编辑模态框
============================================================ */


function createEntityManager(config) {

    const {
        entityName,          // 例如 ingredient
        listId,              // 列表容器ID
        newNameId,           // 新增实体的 input ID
        addBtnId,             // 新增按钮ID
        categoryListId,      // 分类列表容器ID
        newCategoryId,       // 新增分类的 select ID
        //filterCategoryId,    // 分类筛选框ID
        newCategoryNameId,   // 新增分类的 input ID
        entityLabel,         // 实体中文名称，用于提示
        apiBase              // API前缀，例如 api/ingredient
    } = config;

    /* ============================================================
       工具函数
    ============================================================ */

    function htmlEscape(str) {
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    async function request(url, method = 'GET', body = null) {
        const r = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: body ? JSON.stringify(body) : null
        });
        return await r.json();
    }
    function filterModalItems({ categoryId = '', keyword = '', type }) {
        const catId = categoryId ? String(categoryId) : '';
        const query = keyword.trim().toLowerCase();
        document
            .querySelectorAll(`.item[data-type="${type}"]`)
            .forEach(el => {
                const elCatId = el.getAttribute('data-category-id');
                const text = el.textContent.toLowerCase();
                /* =============================
                   分类匹配
                ============================== */
                const matchCategory = !catId || elCatId == catId;
                /* =============================
                   关键词匹配
                ============================== */
                const matchKeyword = !query || text.includes(query);
                /* =============================
                   最终显示
                ============================== */
                el.style.display = (matchCategory && matchKeyword)
                    ? 'flex'
                    : 'none';
            });
    }
    function applyFilter() {
        const keyword = document.getElementById('search_' + entityName)?.value || '';
        const categoryId = document.getElementById('filter_' + entityName + '_category')?.value || '';
        filterModalItems({
            type: entityName,
            keyword,
            categoryId
        });
    }
    /* ============================================================
       初始化
    ============================================================ */
    function init(isCategory = false) {
        if (!isCategory) {
            load();
        }
        loadCategories();
        bindEvents(isCategory);
    }
    /* ============================================================
       绑定事件
    ============================================================ */
    function bindEvents(isCategory = false) {
        const addBtn = document.getElementById(isCategory ? addBtnId + "_category" : addBtnId);
        const addBtn2 = document.getElementById(isCategory ? addBtnId + "_category2" : addBtnId);
        if (addBtn && !addBtn.dataset.bound) {
            addBtn.dataset.bound = '1';
            addBtn.onclick = () => {
                openEditModal(
                    window[entityName + 'Manager'],
                    isCategory ? entityName + '_category' : entityName,
                    null,
                    '',
                    isCategory ? null : 1
                );
            };
        }
        if (addBtn2 && !addBtn2.dataset.bound) {
            const newItemName = document.getElementById(isCategory ? newCategoryNameId : newNameId);
            addBtn2.dataset.bound = '1';
            addBtn2.onclick = () => {
                create({ entityType: isCategory ? entityName + '_category' : entityName, name: newItemName.value, categoryId: isCategory ? null : 1 });
            }
        }
        // 这里也可以顺便绑定筛选（更统一）
        bindFilters();
    }
    function bindFilters() {
        const searchInput = document.getElementById('search_' + entityName);
        const categorySelect = document.getElementById('filter_' + entityName + '_category');

        if (!searchInput && !categorySelect) return;
        if (searchInput && !searchInput.dataset.bound) {
            searchInput.dataset.bound = '1';
            let searchTimer = null;
            searchInput.addEventListener('input', () => {
                clearTimeout(searchTimer);
                searchTimer = setTimeout(applyFilter, 300);
            });
        }
        if (categorySelect && !categorySelect.dataset.bound) {
            categorySelect.dataset.bound = '1';
            categorySelect.addEventListener('change', applyFilter);
        }
    }

    /* ============================================================
       加载实体列表
    ============================================================ */

    function load() {
        apiRequest(apiBase)
            .then(res => {
                if (res.code !== 0) {
                    alert(res.msg || '加载失败');
                    return;
                }
                const container = document.getElementById(listId);
                let html = '';
                if (res.code === 0 && res.data?.length) {
                    res.data.forEach(item => {
                        html += `
                        <div class="item" data-type="${entityName}"
                                data-category-id="${item.category_id ?? ''}">
                            <div class="item-title">
                                ${htmlEscape(item.name)}
                            </div>
                            <div class="item-actions">
                                <button class="btn-small btn-confirm"
                                    onclick="openEditModal(window.${entityName}Manager,
                                        '${entityName}',
                                        ${item.id},
                                        '${htmlEscape(item.name)}',
                                        ${item.category_id ?? 'null'})">
                                    编辑
                                </button>
                                <button class="btn-small btn-cancel"
                                    onclick="window.${entityName}Manager.remove(${item.id})">
                                    删除
                                </button>
                            </div>
                        </div>
                    `;
                    });
                } else {
                    html = `<div class="empty-msg">暂无${entityLabel}</div>`;
                }
                container.innerHTML = html;
                applyFilter();
            });
    }

    /* ============================================================
       删除实体
    ============================================================ */
    let isRemoving = false;
    function remove(id) {
        if (isRemoving) return;
        if (!confirm('确定删除吗？')) return;
        isRemoving = true;
        apiRequest(`${apiBase}/${id}`, 'DELETE')
            .then(res => {
                if (res.code !== 0) {
                    alert(res.msg || '删除失败');
                    return;
                }
                Toast.success('删除成功');
                load();
            })
            .finally(() => {
                isRemoving = false;
            });
    }

    /* ============================================================
       保存编辑（供 editModal 调用）
    ============================================================ */
    let isSaving = false;
    function update({ entityType, id, name, categoryId }) {
        if (isSaving) return;
        const isCategory = entityType.endsWith('_category');

        const url = isCategory
            ? `api/category/${id}?type=${entityName}`
            : `${apiBase}/${id}`;

        const body = isCategory
            ? { name }
            : { name, categoryId };
        isSaving = true;
        return apiRequest(url, 'PUT', body)
            .then(res => {
                if (res.code !== 0) {
                    alert(res.msg || '保存失败');
                    return;
                }
                Toast.success('保存成功');
                if (isCategory) {
                    loadCategories();
                } else {
                    load();
                }
            }).finally(() => {
                isSaving = false;
            });
    }
    /* ============================================================
    新增（供 editModal 调用）
    =========================================================== */
    let isCreating = false;
    function create({ entityType, name, categoryId }) {
        if (isCreating) return;
        const isCategory = entityType.endsWith('_category');
        const url = isCategory
            ? `api/category?type=${entityName}`
            : apiBase;
        const body = isCategory
            ? { name }
            : { name, categoryId };
        isCreating = true;
        return apiRequest(url, 'POST', body)
            .then(res => {
                if (res.code !== 0) {
                    alert(res.msg || '新增失败');
                    return;
                }
                Toast.success('新增成功');
                if (isCategory) {
                    loadCategories();
                } else {
                    load();
                }
            })
            .finally(() => {
                isCreating = false;
            });
    }

    /* ============================================================
       分类加载
    ============================================================ */
    function loadCategories() {
        if (!categoryListId) return;
        apiRequest(`api/category?type=${entityName}`)
            .then(res => {
                if (res.code !== 0) {
                    alert(res.msg || '分类加载失败');
                    return;
                }
                const container = document.getElementById(categoryListId);
                const editSelect = document.getElementById('editCategory');
                const filterSelect = document.getElementById('filter_' + entityName + '_category');
                let html = '';
                if (editSelect) {
                    editSelect.innerHTML = '';
                }
                if (filterSelect) {
                    filterSelect.innerHTML = '<option value="">全部</option>';
                }
                if (res.code === 0 && res.data?.length) {
                    res.data.forEach(cat => {
                        html += `
                        <div class="item">
                            <div class="item-title">
                                ${htmlEscape(cat.name)}
                            </div>
                            <div class="item-actions">

                                <button class="btn-small btn-confirm"
                                    onclick="openEditModal(window.${entityName}Manager,
                                        '${entityName}_category',
                                        ${cat.id},
                                        '${htmlEscape(cat.name)}')">
                                    编辑
                                </button>
                                <button class="btn-small btn-cancel"
                                    onclick="window.${entityName}Manager.removeCategory(${cat.id})">
                                    删除
                                </button>

                            </div>
                        </div>
                    `;
                        const optionHtml = `
                        <option value="${cat.id}">
                            ${htmlEscape(cat.name)}
                        </option>
                    `;
                        if (editSelect) editSelect.innerHTML += optionHtml;
                        if (filterSelect) filterSelect.innerHTML += optionHtml;
                    });
                } else {
                    html = `<div class="empty-msg">暂无${entityLabel}分类</div>`;
                }
                container.innerHTML = html;
                document.getElementById('addBtn').addEventListener('click', () => {
                    openEditModal(
                        window[entityName + 'Manager'], // ✅ 正确获取对象
                        entityName + '_category',
                        null,
                        '',
                        null
                    );
                });
                // ✅ 默认选中第一个
                if (res.data.length > 0) {
                    const firstId = res.data[0].id;
                    if (editSelect) editSelect.value = firstId;
                }
            });
    }
    /* ============================================================
       删除分类
    ============================================================ */
    let isCatRemoving = false;
    function removeCategory(id) {
        if (isCatRemoving) return;
        if (!confirm('确定删除分类吗？')) return;

        isCatRemoving = true;
        apiRequest(`api/category/${id}?type=${entityName}`, 'DELETE')
            .then(res => {
                if (res.code !== 0) {
                    alert(res.msg || '删除失败');
                    return;
                }
                Toast.success('删除成功');
                document.getElementById(newCategoryNameId).value = '';
                loadCategories();
            })
            .finally(() => {
                isCatRemoving = false;
            });
    }
    /* ============================================================
       暴露接口
    ============================================================ */
    const manager = {
        init,
        load,
        //add,
        remove,
        update,
        create,
        loadCategories,
        //addCategory,
        removeCategory
    };

    return manager;
}
const recipeManager = createEntityManager({
    entityName: 'recipe',
    listId: 'recipesList',
    newNameId: 'newRecipeName',
    addBtnId: 'addRecipe',
    //filterCategoryId: 'filterRecipeCategory',
    categoryListId: 'recipeCategoriesList',
    newCategoryNameId: 'newRecipeCatName',
    entityLabel: '菜谱',
    apiBase: 'api/recipe'
});
const ingredientManager = createEntityManager({
    entityName: 'ingredient',
    listId: 'ingredientsList',
    newNameId: 'newIngName',
    addBtnId: 'addIng',
    newCategoryId: 'newIngCategory',
    //filterCategoryId: 'filterIngCategory',
    categoryListId: 'ingCategoriesList',
    newCategoryNameId: 'newIngCatName',
    entityLabel: '食材',
    apiBase: 'api/ingredient'
});

const seasoningManager = createEntityManager({
    entityName: 'seasoning',
    listId: 'seasoningsList',
    newNameId: 'newSeasoningName',
    addBtnId: 'addSea',
    newCategoryId: 'newSeasoningCategory',
    //filterCategoryId: 'filterSeasoningCategory',
    categoryListId: 'seasoningCategoriesList',
    newCategoryNameId: 'newSeasoningCatName',
    entityLabel: '调料',
    apiBase: 'api/seasoning'
});

window.recipeManager = recipeManager;
window.ingredientManager = ingredientManager;
window.seasoningManager = seasoningManager;