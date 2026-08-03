/* import { apiRequest } from './api.js'; */

// 收藏 / 取消收藏
export async function toggleFavorite(recipeId, del = false) {

    const url = `api/favorite/${recipeId}`;
    if (del) {
        await apiRequest(url, 'DELETE');
        return false; // 已取消
    } else {
        await apiRequest('api/favorite', 'POST', {
            recipe_id: recipeId
        });
        return true;
    }
    try {
        // 先尝试删除（如果存在）
        await apiRequest(url, 'DELETE');
        return false; // 已取消
    } catch {
        // 如果删除失败就添加
        await apiRequest('api/favorite', 'POST', {
            recipe_id: recipeId
        });
        return true; // 已收藏
    }
}


// 今日菜单
export function showAddMenu(recipeId) {
    const now = new Date();
    const format = d => d.toLocaleDateString('sv-SE');
    const today = format(now);
    const tomorrow = format(new Date(now.getTime() + 86400000));
    const dayAfterTomorrow = format(new Date(now.getTime() + 2 * 86400000));
    let html = ''
    html += `<button class="btn-normal btn-confirm" onclick="addToMenu(${recipeId},'${today}')">今天</button>
    <button class="btn-normal btn-confirm" onclick="addToMenu(${recipeId},'${tomorrow}')">明天</button>
    <button class="btn-normal btn-confirm" onclick="addToMenu(${recipeId},'${dayAfterTomorrow}')">后天</button>
    <button class="btn-normal btn-confirm" onclick="showDatePicker(${recipeId})">选择日期</button>`
    showModal("加入菜单", html);
}
function showDatePicker(recipeId) {
    const today = new Date().toISOString().split('T')[0];

    const html = `
        <div style="text-align:center;">
            <input type="date" id="menuDate" value="${today}" min="${today}"
                style="padding:8px; border:1px solid #ccc; border-radius:8px;">

            <div style="margin-top:15px;">
                <button class="btn-normal btn-confirm" onclick="confirmDate(${recipeId})">确定</button>
                <button class="btn-normal btn-cancel" onclick="closeModal()">取消</button>
            </div>
        </div>
    `;

    showModal("选择日期", html,false);
}
function confirmDate(recipeId) {
    const date = document.getElementById('menuDate').value;
    if (!date) {
        alert('请选择日期');
        return;
    }
    closeModal();
    addToMenu(recipeId, date);
}
export async function addToMenu(recipeId, date) {
    try {
        const res=await apiRequest('api/menu', 'POST', {
            recipe_id: recipeId,
            date: date
        });
        if (res.code !== 0) {
            alert(res.msg || '添加失败');
            return;
        }else{
            Toast.success("添加成功");
            closeModal();
        }
    } catch (e) {
        alert("添加失败" + e);
    }
}
export async function removeFromMenu(recipeId, date) {
    if (!confirm("确定要移除吗？")) return;
    try {
        await apiRequest('api/menu', 'DELETE', {
            recipe_id: recipeId,
            date: date
        });
    } catch (e) {
        alert("移除失败" + e);

    }

}
export async function toggleDateMenu(recipeId, del = false, date = null) {
    date = date || new Date().toLocaleDateString('sv-SE');
    //const today = new Date().toLocaleDateString('sv-SE');
    if (del) {
        await apiRequest('api/menu', 'DELETE', {
            recipe_id: recipeId,
            date: date
        });
        return false; // 已移除
    } else {
        await apiRequest('api/menu', 'POST', {
            recipe_id: recipeId,
            date: date
        });
        return true; // 已加入
    }


}

/**
 * 自动隐藏按钮模块
 * @param {Object} options
 * @param {string} options.btnId 需要自动隐藏的按钮ID
 * @param {HTMLElement|string} options.container 滚动容器（元素或ID），默认window
 * @param {number} options.threshold 滑动触发阈值
 */
export function initAutoHideButton({
    btnId,
    container = window,
    threshold = 3
} = {}) {

    const btn = document.getElementById(btnId);
    if (!btn) return;
    if (typeof container === 'string') {
        container = document.getElementById(container);
    }
    let lastTouchY = 0;
    function onScroll(e) {
        let direction = 0; // 1 = 下滑, -1 = 上滑
        if (e.type === 'wheel') {
            if (Math.abs(e.deltaY) < threshold) return;
            direction = e.deltaY > 0 ? 1 : -1;
        } else if (e.type === 'touchmove') {
            const currentY = e.touches[0].clientY;
            if (Math.abs(currentY - lastTouchY) < threshold) return;
            if (lastTouchY !== 0) {
                direction = currentY < lastTouchY ? 1 : -1;
            }
            lastTouchY = currentY;
        }
        if (direction === 1) {
            btn.classList.add('hide');
        } else if (direction === -1) {
            btn.classList.remove('hide');
        }
    }

    container.addEventListener('wheel', onScroll, { passive: true });
    container.addEventListener('touchmove', onScroll, { passive: true });

    container.addEventListener(
        'touchstart',
        e => {
            lastTouchY = e.touches[0].clientY;
        },
        { passive: true }
    );
}
window.showAddMenu = showAddMenu;
window.addToMenu = addToMenu;
window.removeFromMenu = removeFromMenu;
window.showDatePicker = showDatePicker;
window.confirmDate = confirmDate;