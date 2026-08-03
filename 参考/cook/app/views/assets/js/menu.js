
//menu.js - 菜单页面逻辑
import { setupInfiniteScroll } from './utils/infiniteScroll.js';
let currentMode = 'single';
let menuDates = [];
let loadFirst = true;


document.querySelectorAll('.mode-btn').forEach(btn => {
    btn.addEventListener('click', function () {
        document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
        this.classList.add('active');
        currentMode = this.dataset.mode;
        document.getElementById('single-mode').style.display =
            currentMode === 'single' ? 'block' : 'none';
        document.getElementById('waterfall-mode').style.display =
            currentMode === 'waterfall' ? 'block' : 'none';

        if (currentMode === 'waterfall') {
            //loadWaterfall();
            waterfallScroll.load(true);
        }
    });
});

// =====================
// 单日模式
// =====================
/* document.getElementById('menuDate').addEventListener('change',function(){
    loadMenuByDate(this.value);
}); */

function loadMenuByDate(date) {
    if (!date) return;
    apiRequest(`api/menu?date=${date}`)
    //fetch(`api/menu?date=${date}`)
        //.then(r => r.json())
        .then(res => {
            let html = '';
            let ingHtml = '';
            if (res.code !== 0) {
                alert(res.msg || '加载失败');
                return;
            }
            const ingredients = res.data.ingList;
            const ingList = document.getElementById('menu-list-ingredients');
            ingList.innerHTML = '';
            if (ingredients && ingredients.length > 0) {
                const lable=document.createElement('label');
                lable.textContent='今日食材：';
                ingList.appendChild(lable);
                ingredients.forEach(ingredient => {
                    const span = document.createElement('span');
                    span.className = 'item-modal';
                    span.textContent = ingredient.name;
                    ingList.appendChild(span);
                });
            }
            const seasonings = res.data.seaList;
            const seaList = document.getElementById('menu-list-seasonings');
            seaList.innerHTML = '';
            if (seasonings && seasonings.length > 0) {
                const lable=document.createElement('label');
                lable.textContent='今日调料：';
                seaList.appendChild(lable);
                seasonings.forEach(seasoning => {
                    const span = document.createElement('span');
                    span.className = 'item-modal';
                    span.textContent = seasoning.name;
                    seaList.appendChild(span);
                })
            }
            //document.getElementById('menu-list-ingredients').innerHTML = ingHtml;
            const recipes = res.data.list;
            if (recipes && recipes.length > 0) {
                recipes.forEach(r => {
                    html += `
                <div class="item" data-id="${r.id}">
                    <div class="item-title" onclick="openRecipeModal(${r.id})" >
                        ${r.title}
                        <div class="item-meta">⏱ ${r.cook_time || '未知'} 分钟</div>
                    </div>
                    <div class="item-actions">
                        <button class="remove-btn btn-small btn-cancel"  data-id="${r.id}" data-date="${date}">
                        删除</button>
                    </div>
                </div>
                `;

                });
            } else {
                html += '<p class="empty-msg">当天没有菜单</p>';
            }
            document.getElementById('list-menu').innerHTML = html;


        });
}

// =====================
// 瀑布流模式
// =====================
const waterfallScroll = setupInfiniteScroll({
    containerOrId: 'waterfall-list',
    urlBuilder: (page, pageSize) =>
        `api/menu?mode=waterfall&page=${page}&pageSize=${pageSize}`,
    renderItem: renderWaterfall,
    pageSize: 10 // 👉 每页加载 5 天
});
function renderWaterfall(days, container) {
    console.log('days', days);
    days.forEach(day => {
        let recipesHtml = '';
        day.recipes.forEach(r => {
            recipesHtml += `
                <div class="item" data-id="${r.id}">
                    <div class="item-title" onclick="openRecipeModal(${r.id})">
                        ${r.title}
                        <div class="item-meta">⏱ ${r.cook_time || '未知'} 分钟</div>
                    </div>
                    <div class="item-actions">
                        <button class="remove-btn btn-small btn-cancel"
                            data-id="${r.id}" data-date="${day.date}">
                            删除
                        </button>
                    </div>
                </div>
            `;
        });
        const html = `
            <div class="day-card">
                <div class="day-title">${day.date}</div>
                <div class="day-recipes">
                    ${recipesHtml}
                </div>
            </div>
        `;
        container.insertAdjacentHTML('beforeend', html);
    });
}
function loadWaterfall() {
    if (!loadFirst) return;
    apiRequest(`api/menu?mode=waterfall`)
    //fetch(`api/menu?mode=waterfall`)
        //.then(r => r.json())
        .then(res => {
            if (res.code !== 0) {
                alert(res.msg || '加载失败');
                return;
            }
            loadFirst = false;
            const listEl = document.getElementById('waterfall-list');
            listEl.innerHTML = '';
            const days = res.data.list;
            if (!days || days.length === 0) {
                listEl.innerHTML = '<p class="empty-msg">暂无菜单记录</p>';
                return;
            }
            days.forEach(day => {
                let recipesHtml = '';
                day.recipes.forEach(r => {
                    recipesHtml += `
                    <div class="item" data-id="${r.id}">
                        <div class="item-title" onclick="openRecipeModal(${r.id})" >
                        ${r.title}
                        <div class="item-meta">⏱ ${r.cook_time || '未知'} 分钟</div>
                    </div>
                    <div class="item-actions">
                        <button class="remove-btn btn-small btn-cancel"  data-id="${r.id}" data-date="${day.date}">
                        删除</button>
                    </div>
                    </div>

                    `;
                });
                const html = `
                    <div class="day-card">
                        <div class="day-title">${day.date}</div>
                        <div class="day-recipes">
                            ${recipesHtml}
                        </div>
                    </div>
                `;
                listEl.insertAdjacentHTML('beforeend', html);
            });
        });
}


// 点击菜谱
document.addEventListener('click', function (e) {
    // 删除按钮
    const removeBtn = e.target.closest('.remove-btn');
    if (removeBtn) {
        deleteMenu(removeBtn.dataset.id, removeBtn.dataset.date);
        return;
    } else {

        // 卡片点击
        const card = e.target.closest('.card');
        if (card) {
            openRecipeModal(card.dataset.id);
        }
    }
});
// 删除菜单
function deleteMenu(recipeId, date) {
    if (!confirm('确定从菜单中删除这道菜吗？')) {
        return;
    }
    apiRequest(`api/menu/${recipeId}?date=${date}`, 'DELETE')
        .then(res => {

            if (res.code !== 0) {
                alert(res.msg || '删除失败');
                return;
            }
            // 删除成功后刷新
            if (currentMode === 'single') {
                loadMenuByDate(date);
                renderCalendar(currentDate);
            } else {
                //loadFirst=true;
                //loadWaterfall();
                waterfallScroll.load(true);
            }

        });

};


let currentDate = new Date();
let selectedDate = null;
function initCalendar() {
    //renderCalendar(currentDate);
    selectedDate = formatDate(new Date());
    renderCalendar(new Date());
    loadMenuByDate(selectedDate);
}
function renderCalendar(date) {

    const year = date.getFullYear();
    const month = date.getMonth() + 1;
    const monthStr = `${year}-${String(month).padStart(2, '0')}`;
    apiRequest(`api/menu?month=${monthStr}`)
    //fetch(`api/menu?month=${monthStr}`)
        //.then(r => r.json())
        .then(res => {
            menuDates = res.data?.dates || [];
            buildCalendar(date);
        });
}

function buildCalendar(date) {
    const year = date.getFullYear();
    const month = date.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const startWeekDay = firstDay.getDay();
    const totalDays = lastDay.getDate();
    const todayStr = formatDate(new Date());
    let html = `
        <div class="calendar">
            <div class="calendar-header">
                <button onclick="changeMonth(-1)">‹</button>
                <div>${year} - ${month + 1}</div>
                <button onclick="changeMonth(1)">›</button>
            </div>
            <div class="calendar-grid">
    `;

    const weekNames = ['日', '一', '二', '三', '四', '五', '六'];
    weekNames.forEach(w => {
        html += `<div class="calendar-weekday">${w}</div>`;
    });

    for (let i = 0; i < startWeekDay; i++) {
        html += `<div></div>`;
    }

    for (let d = 1; d <= totalDays; d++) {

        const dateStr = formatDate(new Date(year, month, d));
        let className = 'calendar-day';
        if (dateStr === todayStr) {
            className += ' today';
        }
        if (dateStr === selectedDate) {
            className += ' selected';
        }
        if (menuDates.includes(dateStr)) {
            className += ' has-menu';
        }
        html += `
            <div class="${className}"
                 onclick="selectDate('${dateStr}')">
                ${d}
            </div>
        `;
    }
    html += `</div></div>`;
    document.getElementById('calendar').innerHTML = html;
}

function changeMonth(offset) {
    currentDate.setMonth(currentDate.getMonth() + offset);
    renderCalendar(currentDate);
}

function selectDate(dateStr) {
    selectedDate = dateStr;
    renderCalendar(currentDate);
    loadMenuByDate(dateStr);
}

function formatDate(date) {
    return date.toLocaleDateString('sv-SE').split('T')[0];
}
initCalendar();

// 默认选中今天
window.selectDate=selectDate;
window.changeMonth=changeMonth;