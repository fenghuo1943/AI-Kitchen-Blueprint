//let userId = 0;
function createCard(recipe) {

    const item = document.createElement('div');
    item.className = 'item';
    const titleDiv = document.createElement('div');
    titleDiv.className = 'item-title';
    titleDiv.textContent = recipe.title;
    const metaDiv = document.createElement('div');
    metaDiv.className = 'item-meta';
    metaDiv.textContent = `⏱ ${recipe.cook_time} min | 👁 ${recipe.view_count}`;
    titleDiv.appendChild(metaDiv);
    titleDiv.addEventListener('click', () => openRecipeModal(recipe.id));
    item.appendChild(titleDiv);
    if (userId > 0) {
        const actionDiv = document.createElement('div');
        actionDiv.className = 'item-actions';
        const favoriteBtn = document.createElement('button');
        favoriteBtn.className = 'btn-small';
        favoriteBtn.classList.toggle('btn-confirm', !recipe.is_favorited);
        favoriteBtn.classList.toggle('btn-cancel', recipe.is_favorited);
        favoriteBtn.textContent = `${recipe.is_favorited ? '取消' : ''}收藏`;
        favoriteBtn.addEventListener('click', () => favoriteClick(recipe.id, favoriteBtn));
        actionDiv.appendChild(favoriteBtn);
        //加入菜单按钮
        const addMenuBtn = document.createElement('button');
        addMenuBtn.className = 'btn-small';
        addMenuBtn.classList.toggle('btn-confirm', !recipe.is_in_today_menu);
        addMenuBtn.classList.toggle('btn-cancel', recipe.is_in_today_menu);
        addMenuBtn.style.maxWidth = '100px';
        addMenuBtn.textContent = `${recipe.is_in_today_menu ? '删除' : '加入'}菜单`;
        addMenuBtn.addEventListener('click', () => todayMenuClick(recipe.id, addMenuBtn));
        actionDiv.appendChild(addMenuBtn);
        item.appendChild(actionDiv);
    }
    return item;
    return `
    <article class="recipe-card" onclick="location.href='/recipe/${recipe.id}'">

    <img src="${recipe.cover}">

    <div class="card-body">

    <h3>${recipe.title}</h3>

    <div class="meta">
    <span>⏱ ${recipe.cook_time} min</span>
    <span>👁 ${recipe.view_count}</span>
    </div>

    </div>

    </article>
    `;

}



function createSkeleton() {
    return `<div class="skeleton skeleton-card"></div>`;
}
function renderSkeleton(container) {
    let html = '';
    for (let i = 0; i < 6; i++) {
        html += createSkeleton();
    }
    container.innerHTML = html;

}
async function loadSection(url, containerId) {
    const container = document.getElementById(containerId);
    //renderSkeleton(container);
    try {
        //const res = await fetch(url);
        //const res = await apiRequest(url);
        const json = await apiRequest(url);
        let html = '';
        if (json.code !== 0) {
            throw new Error(json.message);
        }
        if (!json.data || json.data.length === 0) {
            container.innerHTML = '<div class="empty-msg">暂无数据</div>';
            return;
        }
        const fragment = document.createDocumentFragment();
        json.data.forEach(recipe => {
            fragment.appendChild(createCard(recipe));
            //html += createCard(recipe);
        });
        //container.innerHTML = html;
        container.innerHTML = '';
        container.appendChild(fragment);

    } catch (e) {
        container.innerHTML = e.message;
    }

}

const user = getProfile();
user.then(user => {
    if (user.code !== 0) {
        //window.location.href = '/cook/auth?redirect=' + (window.location.pathname) + window.location.hash;
    }
    else {
        userId = user.data['id'];
        loadSection("api/discover?type=today", "today-grid");
        loadSection("api/discover?type=random", "random-grid");
        loadSection("api/discover?type=new", "recent-grid");
    }
})


document.getElementById("randomBtn").addEventListener("click", function () {
    loadSection("api/discover?type=random", "random-grid");
});
