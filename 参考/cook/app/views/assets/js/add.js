/* import { apiRequest } from "./utils/api"; */

// add.js
const hash = location.hash.slice(1); // 去掉 #
const params = new URLSearchParams(hash);
const recipeId = params.get('id');
//let userId = 0;
const user = getProfile();
user.then(user => {
    if (user.code !== 0) {
        window.location.href = '/cook/auth?redirect=' + (window.location.pathname) + window.location.hash;
    }
    else {
        userId = user.data['id'];
    }
})


let allData = {
    categories: [],
    ingredients: [],
    seasonings: [],
    seaCategories: [],
    ingCategories: []
};

let selected = {
    categories: {},
    ingredients: {},
    seasonings: {}
};
document.addEventListener("DOMContentLoaded", async () => {
    addStep();
    if (recipeId) {
        document.getElementById("formTitle").textContent = "编辑菜谱";
        await loadRecipe(recipeId);
        requestAnimationFrame(() => autoTextareaHeight(desc));
    }
    allData.ingCategories = await loadData('api/category?type=ingredient');
    allData.categories = await loadData('api/category?type=recipe');
    allData.seaCategories = await loadData('api/category?type=seasoning');
    allData.ingredients = await loadData('api/ingredient');
    allData.seasonings = await loadData('api/seasoning');
    document.getElementById('btnBack')
        .addEventListener('click', goBack);
    document.getElementById('btnCat')
        .addEventListener('click', openCategoryModal);
    document.getElementById('btnIng')
        .addEventListener('click', openIngredientModal);
    document.getElementById('btnSea')
        .addEventListener('click', openSeasoningModal);
    document.getElementById('btnAddStep')
        .addEventListener('click', ()=>{addStep();});


});
const desc = document.getElementById("description");
desc.addEventListener("input", () => autoTextareaHeight(desc));
// =========================
// 通用 API
// =========================
async function loadData(api) {
    try {
        //const r = await fetch(api);
        const res = await apiRequest(api);
        return res.code === 0 ? res.data : [];
    } catch (e) {
        console.error('请求失败', e);
        return [];
    }
}

// =========================
// 加载菜谱
// =========================
async function loadRecipe(id) {
    //const r = await fetch(`api/recipe?id=${id}`);
    const res = await apiRequest(`api/recipe?id=${id}`);
    const data = res.data;
    document.getElementById("title").value = data.recipe.title;
    document.getElementById("description").value = data.recipe.description;
    document.getElementById("cook_time").value = data.recipe.cook_time;
    data.categories.forEach(c => {
        selected.categories[c.id] = { name: c.name };
    });
    data.ingredients.forEach(i => {
        selected.ingredients[i.id] = {
            name: i.name,
            quantity: i.quantity || ''
        };
    });
    data.seasonings.forEach(s => {
        selected.seasonings[s.id] = {
            name: s.name,
            quantity: s.quantity || ''
        };
    });
    document.getElementById("stepsBox").innerHTML = '';
    data.steps.forEach(s => addStep(s.content));
    updateChosenList('categories');
    updateChosenList('ingredients', true);
    updateChosenList('seasonings', true);
}
// =========================
// Modal
// =========================
function openCategoryModal() {
    openSelectModal({
        title: '选择分类',
        api: 'api/category?type=recipe',
        type: 'categories'
    });
}
function openIngredientModal() {
    openSelectModal({
        title: '选择食材',
        api: 'api/ingredient',
        type: 'ingredients',
        withQuantity: true,
        hasCategory: true
    });
}
function openSeasoningModal() {
    openSelectModal({
        title: '选择调料',
        api: 'api/seasoning',
        type: 'seasonings',
        withQuantity: true,
        hasCategory: true
    });
}
async function openSelectModal({
    title,
    api,
    type,
    hasCategory = false,
    withQuantity = false
}) {
    let html = '';
    let catData=[];
    html += `<div class="selectModal-row">
                <input id="modalSearch" placeholder="搜索" autocomplete="off"
                    oninput="filterModalItems(this.value,'${type}')">`;
    if (hasCategory) {
        if(type==='ingredients'){
            catData = allData.ingCategories;
        }else if(type==='seasonings'){
            catData = allData.seaCategories;
        }
        html += `<select id="ingCategoryFilter"
                onchange="filterModalItemsByCategory(this.value)">`;
        html += `<option value="">全部分类</option>`;
        catData.forEach(cat => {
            html += `<option value="${cat.id}">${cat.name}</option>`;
        });
        html += `</select>`;
    }
    html += `</div>`
    html += `<div id="modalList" class="selectModal-list"></div>`;
    html += `
        <div class="selectModal-row">
            <input id="newItemName" placeholder="名称" autocomplete="off">`
    if (hasCategory) {
        html += `<select id="newIngCategory">`
        catData.forEach(cat => {
            let selected = cat.name === '默认' ? ' selected' : '';
            html += `<option value="${cat.id}" ${selected}>${cat.name}</option>`;
        });
        html += `</select>`;
    }
    html += `<button id="btnAdditem" class="btn-small btn-confirm">添加</button>
        </div>
    `;
    showModal(title, html);
    document.getElementById('btnAdditem')
        .addEventListener('click', ()=>{addItem({api,type,withQuantity,hasCategory});});
    //const data = await loadData(api);
    //allData[type] = data;
    const data = allData[type];
    renderList({
        data,
        type,
        withQuantity,
        hasCategory
    });
}
// =========================
// 渲染列表
// =========================
function renderList({
    data,
    type,
    withQuantity = false,
    hasCategory = false
}) {
    const list = document.getElementById('modalList');
    list.innerHTML = '';
    data.forEach(item => {
        const span = document.createElement('span');
        span.className = 'item-modal';
        if (selected[type][item.id]) {
            span.classList.add('selected');
        }
        span.dataset.id = item.id;
        span.dataset.type = type;
        if (hasCategory) {
            span.dataset.categoryId = item.category_id;
        }
        span.textContent = item.name;
        span.onclick = () => toggleSelected({
            id: item.id,
            name: item.name,
            type,
            withQuantity,
            el: span
        });
        list.appendChild(span);
    });
}
// =========================
// 选择逻辑
// =========================
function toggleSelected({ id, name, type, withQuantity, el }) {
    if (selected[type][id]) {
        delete selected[type][id];
        el.classList.remove('selected');
    } else {
        selected[type][id] = {
            name,
            quantity: withQuantity ? '' : undefined
        };
        el.classList.add('selected');
    }
    updateChosenList(type, withQuantity);
}
// =========================
// 已选列表
// =========================
function updateChosenList(type, withQuantity = false) {
    const box = document.getElementById(type + "List");

    if (!box) return;
    box.innerHTML = '';
    for (let id in selected[type]) {
        const item = selected[type][id];
        const div = document.createElement('div');
        div.className = 'item-chosen';
        const span = document.createElement('span');
        span.textContent = item.name;
        div.appendChild(span);
        const input = document.createElement('input');
        if (withQuantity) {
            input.value = item.quantity || '';
            input.placeholder = '数量';
            input.addEventListener('input', e => {
                item.quantity = e.target.value;
                autoWidth(e.target);
            });
            div.appendChild(input);
        }
        const remove = document.createElement('span');
        remove.textContent = '×';
        remove.onclick = () => {
            delete selected[type][id];
            updateChosenList(type, withQuantity);
        };
        div.appendChild(remove);
        box.appendChild(div);
        if (withQuantity)
            requestAnimationFrame(() => autoWidth(input));
    }
}
// =========================
// 添加项目
// =========================
let isAdding = false;
async function addItem({api, type, withQuantity,hasCategory}) {
    if (isAdding) return;
    const input = document.getElementById('newItemName');
    const name = input.value.trim();
    if (!name) return alert('名称不能为空');
    isAdding = true;
    //Toast.show('添加中...');
    try {
        /* const r = await fetch(api, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name })
    }); */
    const body = { name };
    if(hasCategory){
        body.categoryId = document.getElementById('newIngCategory').value;
    }
        const res = await apiRequest(api, 'POST', body);
        //isAdding = false;
        if (res.code === 0) {
            const id = res.data.id;
            selected[type][id] = {
                name,
                quantity: withQuantity ? '' : undefined
            };
            input.value = '';
            const data = await loadData(api);
            allData[type] = data;
            renderList({ data, type, withQuantity });
            updateChosenList(type, withQuantity);
            Toast.success('添加成功');
        } else {
            alert(res.msg || '添加失败');
        }
    } finally {
        isAdding = false;
    }

}

// =========================
// Step
// =========================
function addStep(value = '') {
    const box = document.getElementById("stepsBox");

    const textarea = document.createElement("textarea");
    textarea.className = "step";
    textarea.placeholder = "步骤";
    textarea.value = value;
    textarea.addEventListener("input", () => autoTextareaHeight(textarea));
    box.appendChild(textarea);

    // 初始化高度
    requestAnimationFrame(() => autoTextareaHeight(textarea));
}
function autoTextareaHeight(el) {
    el.style.height = 'auto';
    el.style.height = el.scrollHeight + 'px';
}
// =========================
// 提交
// =========================
document.querySelectorAll(".submitRecipe").forEach(btn => {
    btn.addEventListener("click", async e => {
        e.preventDefault();
        submitData();
    });
});
let isSubmitting = false;
async function submitData() {
    if (isSubmitting) return;
    const title = document.getElementById("title").value;
    if (!title) return alert('请填写标题');
    const steps = [...document.querySelectorAll(".step")]
        .map(s => s.value)
        .filter(s => s.trim());
    const payload = {
        title,
        description: document.getElementById("description").value,
        cook_time: document.getElementById("cook_time").value,
        category_ids: Object.keys(selected.categories),
        ingredients: Object.entries(selected.ingredients).map(([id, v]) => ({
            id,
            quantity: v.quantity
        })),
        seasonings: Object.entries(selected.seasonings).map(([id, v]) => ({
            id,
            quantity: v.quantity
        })),
        steps
    };
    const method = recipeId ? "PUT" : "POST";
    const url = recipeId
        ? `api/recipe?id=${recipeId}`
        : `api/recipe`;
    isSubmitting = true;
    //Toast.show('保存中...');
    /* const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    }); */
    const result = await apiRequest(url, method, payload);
    isSubmitting = false;
    if (result.code === 0) {
        Toast.success('保存成功');
        goBack();
    } else {
        alert(result.message || "保存失败");
    }
}
// =========================
// 工具
// =========================
function autoWidth(input) {
    if (input.value !== '') {
        input.style.width = '0px';
        input.style.width = (input.scrollWidth + 6) + 'px';
    }
}
//const textarea = document.getElementById("desc");



function filterModalItems(query, type) {
    query = query.toLowerCase();
    document.querySelectorAll(`.item-modal[data-type="${type}"]`)
        .forEach(el => {
            el.style.display =
                el.textContent.toLowerCase().includes(query)
                    ? 'inline-block'
                    : 'none';
        });
}
function filterModalItemsByCategory(catId) {
    document.querySelectorAll('.item-modal').forEach(el => {
        if (!catId) {
            el.style.display = '';
        } else {
            el.style.display =
                el.dataset.categoryId == catId
                    ? 'inline-block'
                    : 'none';
        }
    });
}


function goBack() {
    const page = params.get("page") || '';
    let loc = '/cook/';
    if (page !== '') {
        //location.href = `/cook/me#recipes`;
        loc += 'me';
    } else {
        loc += 'home';
    }
    location.href = loc + '#' + params.toString();

}
