// recipe_modal.js
import { apiRequest } from './utils/api.js';
import { initAutoHideButton, showAddMenu} from './utils/func.js';

const modal = document.getElementById('recipeModal');
const modalBody = document.getElementById('recipeModalBody');
const backhtml = `<div class="page-header">
                    <div class="btn-back" onclick="closeRecipeModal()">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                            <path d="M19 12H6" stroke="#0784ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                            <path d="M12 19L5 12L12 5" stroke="#0784ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                    </div>`

function openRecipeModal(recipeId) {
    modalBody.innerHTML = backhtml + '</div><div class="loading">加载中...</div>';
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
    const hash = location.hash.slice(1); // 去掉 #
    const params = new URLSearchParams(hash);
    //console.log(params.toString());
    const page = params.get("page") || '';
    history.pushState({ modalOpen: true }, '', '#' + (page !== '' ? 'page=' + page + '&' : '') + 'id=' + recipeId);
    apiRequest(`api/recipe&id=${recipeId}`)
        //fetch(`api/recipe&id=${recipeId}`)
        //.then(res => res.json())
        .then(data => {
            if (data.code === 0) {
                renderRecipeDetail(data.data);
                //initMenuBtnAutoHide();
                initAutoHideButton({
                    btnId: 'addMenuBtn',
                    container: modal,
                    threshold: 3
                });
            } else {
                modalBody.innerHTML = `<div class="loading">加载失败: ${data.error}</div>`;
            }
        })
        .catch(err => {
            console.error(err);
            modalBody.innerHTML = '<div class="loading">加载出错</div>';
        });

}

function renderRecipeDetail(data) {
    const { recipe, ingredients, seasonings, steps, is_favorite, categories, is_in_today_menu } = data;
    document.title = recipe.title + ' - 菜谱详情';

    let html = backhtml;
    html += `<h2 >${recipe.title}</h2>`;
    if (userId > 0) {
        html += `<div id="modalFavBtn" class="recipe-modal-favorite" data-id="${recipe.id}">${is_favorite ? '❤️' : '🤍'}</div>`;
        html += `<div class="recipe-modal-edit" onclick="editRecipe(${recipe.id})">`;
        html += `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">`;
        html += `<path d="M11 4H4C3.46957 4 2.96086 4.21071 2.58579 4.58579C2.21071 4.96086 2 5.46957 2 6V20C2 20.5304 2.21071 21.0391 2.58579 21.4142C2.96086 21.7893 3.46957 22 4 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V13" stroke="#0784ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>`;
        html += `<path d="M18.5 2.5C18.8978 2.10217 19.4374 1.87868 20 1.87868C20.5626 1.87868 21.1022 2.10217 21.5 2.5C21.8978 2.89782 22.1213 3.43742 22.1213 4C22.1213 4.56258 21.8978 5.10217 21.5 5.5L12 15L8 16L9 12L18.5 2.5Z" stroke="#0784ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>`;
        html += `</svg>`;
        html += `<span>编辑菜谱</span>`;
        html += `</div>`;
    }
    html += `</div>`;
    // 封面图片
    if (recipe.cover) {
        html += `<img class="recipe-modal-cover" src="/uploads/recipes/${recipe.cover}" alt="${recipe.title}">`;
    }

    //html += `<div class="recipe-modal-meta">⏱ ${recipe.cook_time || '未知'} 分钟</div>`;
    if (recipe.description) {
        html += `<div class="recipe-modal-section"><h3>简介</h3>`;
        html += `<div class="recipe-modal-description">${recipe.description.replace(/\n/g, '<br>')}</div>`;
        html += `</div>`;
    }
    html += `<div class="recipe-modal-section"><h3>食材清单</h3>`;
    if (ingredients.length) {
        html += `<div class="recipe-modal-list-small">`
        ingredients.forEach(i => html += `<span class="recipe-modal-item-small">${i.name}${i.quantity ? '-' + i.quantity : ''}</span>`);
        html += `</div>`
    } else {
        html += `<div class="empty-msg" sytle="padding:10px;">暂无食材信息</div>`;
    }
    html += `</div>`

    html += `<div class="recipe-modal-section"><h3>调料</h3>`;
    //html += `<ul>`;

    if (seasonings && seasonings.length) {
        html += `<div class="recipe-modal-list-small">`;
        seasonings.forEach(s => {
            html += `<span class="recipe-modal-item-small">${s.name}${s.quantity ? '-' + s.quantity : ''}</span>`;
        });
        html += `</div>`
    } else {
        html += `<div class="empty-msg" sytle="padding:10px;">暂无调料信息</div>`;
    }

    html += `</div>`

    html += `<div class="recipe-modal-section"><h3>制作步骤</h3>`;
    //html += `<ol>`;
    if (steps.length) {
        html += `<div class="recipe-modal-list-large">`;
        steps.forEach(s => {
            html += `<li class="recipe-modal-item-large">${s.content.replace(/\n/g, '<br>')}</li>`
        });
        html += `</div>`
    } else {
        html += `<div class="empty-msg" sytle="padding:10px;">暂无步骤信息</div>`;
    }
    html += `</div>`;
    html += `
        <div id="addMenuBtn"
            class="recipe-add-menu-btn ${is_in_today_menu ? 'added' : ''}"
            data-id="${recipe.id}"
            onclick="showAddMenu(${recipe.id})">
            加入菜单
        </div>
        `;
    modalBody.innerHTML = html;

    const favBtn = document.getElementById('modalFavBtn');
    if (favBtn) {
        favBtn.addEventListener('click', () => toggleFavorite(favBtn.dataset.id, favBtn));
    }
}
function closeRecipeModal() {
    modal.classList.remove('active');
    document.body.style.overflow = '';
    document.title = '菜谱';
    const hash = location.hash.slice(1);
    const params = new URLSearchParams(hash);

    const page = params.get("page");

    if (page) {
        history.replaceState({}, '', '#page=' + page);
    } else {
        history.replaceState({}, '', location.pathname);
    }
}

window.addEventListener('popstate', e => {
    if (modal.classList.contains('active')) closeRecipeModal();
});

// 收藏功能
function toggleFavorite(recipeId, btn) {
    const isFavorited = btn.innerHTML.trim() === '❤️';

    let url = 'api/favorite';
    let method = 'POST';
    let options = {
        headers: { 'Content-Type': 'application/json' }
    };
    if (isFavorited) {
        // 取消收藏
        method = 'DELETE';
        url = `api/favorite/${recipeId}`;
        options.body = null;
    } else {
        // 添加收藏
        options.body = JSON.stringify({
            recipe_id: recipeId
        });
    }
    apiRequest(url, method, { recipe_id: recipeId })
        /* fetch(url, {
            method: method,
            ...options
        }) */
        //.then(res => res.json())
        .then(data => {
            if (data.code === 0) {
                btn.innerHTML = isFavorited ? '🤍' : '❤️';
            } else {
                alert(data.msg || '操作失败');
            }
        })
        .catch(() => alert('操作失败，请稍后重试'));
}
// 加入今日菜单
function toggleDateMenu(recipeId, btn) {
    const today = new Date().toLocaleDateString('sv-SE');
    console.warn(today);
    const isAdded = btn.classList.contains('added');
    let body = { recipe_id: recipeId, data: today };
    let method = 'POST';
    if (isAdded) {
        method = 'DELETE';
    }
    apiRequest('api/menu', method, body)
        .then(data => {
            if (data.code === 0) {
                if (isAdded) {
                    btn.classList.remove('added');
                    btn.innerHTML = '➕ 加入今日菜单';
                    Toast.success('已从今日菜单中移除 ❌');
                } else {
                    btn.innerHTML = '✅ 已在今日菜单';
                    btn.classList.add('added');
                    Toast.success('已加入今日菜单 ✅');
                }

            } else {
                Toast.error(data.msg || '加入失败');
            }
        })
        .catch(() => Toast.error('网络错误，请稍后重试'));
}
function initMenuBtnAutoHide() {
    const btn = document.getElementById('addMenuBtn');
    if (!btn) return;
    let lastScrollY = window.scrollY;
    let lastTouchY = 0;
    function onScroll(e) {
        const btn = document.getElementById('addMenuBtn');
        if (!btn) return;
        let direction = 0; // 1 = 下滑, -1 = 上滑
        if (e.type === 'wheel') {
            // 鼠标滚轮
            if (Math.abs(e.deltaY) < 3) return;
            direction = e.deltaY > 0 ? 1 : -1;
        } else if (e.type === 'touchmove') {
            const currentY = e.touches[0].clientY;
            if (Math.abs(currentY - lastTouchY) < 3) return;
            // 手指滑动
            if (lastTouchY !== 0) {
                direction = currentY < lastTouchY ? 1 : -1;
            }
            lastTouchY = currentY;
        }
        console.log(direction);
        if (direction === 1) {
            // 向下滑 -> 隐藏
            btn.classList.add('hide');
        } else if (direction === -1) {
            // 向上滑 -> 显示
            btn.classList.remove('hide');
        }
    }

    modal.addEventListener('wheel', onScroll, { passive: true });
    modal.addEventListener('touchmove', onScroll, { passive: true });
    modal.addEventListener('touchstart', e => {
        lastTouchY = e.touches[0].clientY;
    }, { passive: true });
    let ticking = false;


}

// 编辑菜谱功能
function editRecipe(recipeId) {
    // 关闭当前模态框
    closeRecipeModal();
    // 跳转到编辑页面
    const hash = location.hash.slice(1); // 去掉 #
    const params = new URLSearchParams(hash);
    //const recipeId = params.get('id')||0;
    window.location.href = `/cook/add` + '#' + params.toString() + '&id=' + recipeId;
}

window.openRecipeModal = openRecipeModal;
window.closeRecipeModal = closeRecipeModal;
window.editRecipe = editRecipe;
//window.toggleFavorite=toggleFavorite;
window.toggleDateMenu = toggleDateMenu;