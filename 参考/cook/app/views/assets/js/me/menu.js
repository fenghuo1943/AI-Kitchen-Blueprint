import { initAutoHideButton } from '../utils/func.js';
let currentPage = 'menu';
//let userId = 0;

const user = getProfile();
user.then(user => {
    if (user.code !== 0) {
        window.location.href = '/cook/auth?redirect=' + (window.location.pathname);
    }
    else {
        userId = user.data['id'];
        document.getElementById('userName').innerText = user.data['username'];
    }
});
initAutoHideButton({ btnId: 'addBtn' });
/* i*/
/* 页面路由表 */
const pageRouter = {
    menu: {
        id: 'menuPage'
    },
    favorites: {
        id: 'favoritesPage',
        load: () => loadFavorites()
    },
    history: {
        id: 'historyPage',
        load: () => loadHistory()
    },
    settings: {
        id: 'settingsPage'
    },
    recipes: {
        id: 'recipesPage',
        load: () => loadRecipes()
    },
    categories: {
        id: 'categoriesPage',
        load: () => recipeManager.init(true)
    },
    ingredients: {
        id: 'ingredientsPage',
        load: () => {
            ingredientManager.init(false);
            //ingredientManager.loadCategories();
        }
    },
    "ing-categories": {
        id: 'ingCategoriesPage',
        load: () => ingredientManager.init(true)
    },
    seasonings: {
        id: 'seasoningsPage',
        load: () => {
            seasoningManager.init(false);
            //seasoningManager.loadCategories();
        }
    },
    "seasoning-categories": {
        id: 'seasoningCategoriesPage',
        load: () => seasoningManager.init(true)
    },
    deletedRecipes: {
        id: 'deletedRecipesPage',
        load: () => loadDeletedRecipes()
    }
};
/* 隐藏头像的页面 */
const hideProfilePages = new Set([
    'favorites',
    'history',
    'settings',
    'categories',
    'ingredients',
    'ing-categories',
    'recipes',
    'seasonings',
    'seasoning-categories',
    'deletedRecipes'
]);
/* 页面跳转 */
function goToPage(pageName, addHistory = true, id = 0) {
    const page = pageRouter[pageName];
    if (!page) return;
    /* history */
    if (addHistory || id != 0) {
        history.pushState({ page: pageName }, '', '#page=' + pageName);
    }
    /* 隐藏所有页面 */
    document.querySelectorAll('.content-page, #menuPage').forEach(el => {
        el.classList.remove('active');
    });
    /* 显示当前页面 */
    const el = document.getElementById(page.id);
    if (el) el.classList.add('active');
    /* 页面加载函数 */
    if (page.load) page.load();
    /* 控制头像显示 */
    const profileHeader = document.querySelector('.profile-header');
    if (profileHeader) {
        profileHeader.style.display =
            hideProfilePages.has(pageName) ? 'none' : 'block';
    }
    currentPage = pageName;

    if (id) {
        openRecipeModal(id);
    }

}
/* 返回 */
function goBack() {
    history.back();
}
/* 浏览器回退 */
window.addEventListener('popstate', (e) => {
    const page = e.state?.page || 'menu';
    if (page == 'menu') {
        history.replaceState({}, '', window.location.pathname + window.location.search);
    }
    goToPage(page, false);
});
/* 页面加载时根据 hash 跳转 */
window.addEventListener('load', () => {
    const hash = location.hash.slice(1); // 去掉 #
    const params = new URLSearchParams(hash);
    const page = params.get("page") || '';
    const id = params.get("id") || 0;
    if (page !== '' && pageRouter[page]) {
        goToPage(page, false, id);

    }

});
function logout() {
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    window.location.href = '/cook';
}
/* 全局 */
window.goToPage = goToPage;
window.goBack = goBack;
window.logout = logout;