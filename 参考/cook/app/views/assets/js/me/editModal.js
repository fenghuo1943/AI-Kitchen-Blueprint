/* ============================================================
   公共编辑模态框控制器
   支持多 Manager 复用
============================================================ */

let currentManager = null;
let currentEntityType = null;

/**
 * 打开编辑模态框
 * @param manager        当前实体管理器
 * @param entityType     实体类型 (ingredient / seasoning / xxx_category)
 * @param id             实体ID
 * @param name           名称
 * @param categoryId     分类ID (可选)
 */
function openEditModal(manager, entityType, id = null, name = '', categoryId = null) {

    currentManager = manager;
    currentEntityType = entityType;

    const isEdit = id !== null && id !== undefined;

    const idInput = document.getElementById('editId');
    const nameInput = document.getElementById('editName');
    const categorySelect = document.getElementById('editCategory');
    const title = document.getElementById('editTitle');

    // 判断是否是分类
    const isCategory = entityType.endsWith('_category');

    /* =============================
       填充 / 清空数据
    ============================== */
    idInput.value = isEdit ? id : '';
    nameInput.value = isEdit ? name : '';

    if (isCategory) {
        categorySelect.style.display = 'none';
    } else {
        categorySelect.style.display = 'block';
        categorySelect.value = categoryId ?? 1;
    }
    /* =============================
       标题控制（关键优化）
    ============================== */
    if (isCategory) {
        title.innerText = isEdit ? '编辑分类' : '新增分类';
    } else {
        title.innerText = isEdit ? '编辑' : '新增';
    }
    /* =============================
       打开弹窗
    ============================== */
    document.getElementById('editModal').style.display = 'flex';
}


/**
 * 保存编辑
 */
function saveEdit() {

    if (!currentManager) return;

    const id = document.getElementById('editId').value;
    const name = document.getElementById('editName').value.trim();
    const categoryId = document.getElementById('editCategory').value || null;

    if (!name) {
        alert('名称不能为空');
        return;
    }

    const isEdit = id !== '' && id !== null && id !== undefined;

    /* =============================
       统一参数
    ============================== */
    const payload = {
        entityType: currentEntityType,
        name: name,
        categoryId: categoryId ? parseInt(categoryId) : null
    };

    /* =============================
       分支逻辑（关键）
    ============================== */
    if (isEdit) {
        payload.id = parseInt(id);
        // 编辑
        if (typeof currentManager.update === 'function') {
            currentManager.update(payload);
        } else {
            // 兼容旧写法
            currentManager.saveEdit(
                currentEntityType,
                payload.id,
                payload.name,
                payload.categoryId
            );
        }
    } else {
        // 新增
        if (typeof currentManager.create === 'function') {
            currentManager.create(payload);
        } else {
            // 兼容旧写法（如果你还没拆 create）
            currentManager.saveEdit(
                currentEntityType,
                null,
                payload.name,
                payload.categoryId
            );
        }
    }

    closeEditModal();
}


/**
 * 关闭模态框
 */
function closeEditModal() {

    document.getElementById('editModal').style.display = 'none';

    currentManager = null;
    currentEntityType = null;
}


/* ============================================================
   事件绑定
============================================================ */

document.getElementById('btnSaveEdit')
    .addEventListener('click', saveEdit);

document.getElementById('btnCancelEdit')
    .addEventListener('click', closeEditModal);