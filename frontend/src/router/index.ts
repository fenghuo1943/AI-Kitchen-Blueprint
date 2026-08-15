/** 路由配置 */
import { createRouter, createWebHistory } from 'vue-router';

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('../views/Home.vue'),
      meta: { title: '首页' }
    },
    {
      path: '/recipes',
      name: 'recipes',
      component: () => import('../views/Recipes.vue'),
      meta: { title: '菜谱库' }
    },
    {
      path: '/recipes/manage',
      name: 'recipe-manage',
      component: () => import('../views/RecipeManagement.vue'),
      meta: { title: '菜谱管理' }
    },
    {
      path: '/recipes/new',
      name: 'recipe-new',
      component: () => import('../views/RecipeForm.vue'),
      meta: { title: '新建菜谱' }
    },
    {
      path: '/recipes/:id',
      name: 'recipe-detail',
      component: () => import('../views/RecipeDetail.vue'),
      meta: { title: '菜谱详情' }
    },
    {
      path: '/recipes/:id/edit',
      name: 'recipe-edit',
      component: () => import('../views/RecipeForm.vue'),
      meta: { title: '编辑菜谱' }
    },
    {
      path: '/menu',
      name: 'menu',
      component: () => import('../views/Menu.vue'),
      meta: { title: '菜单' }
    },
    {
      path: '/discover',
      name: 'discover',
      component: () => import('../views/Discover.vue'),
      meta: { title: '发现' }
    },
    {
      path: '/favorites',
      name: 'favorites',
      component: () => import('../views/Favorites.vue'),
      meta: { title: '我的收藏' }
    },
    {
      path: '/history',
      name: 'history',
      component: () => import('../views/History.vue'),
      meta: { title: '浏览历史' }
    },
    {
      path: '/recycle-bin',
      name: 'recycle-bin',
      component: () => import('../views/RecycleBin.vue'),
      meta: { title: '回收站' }
    },
    {
      path: '/categories',
      name: 'categories',
      component: () => import('../views/Categories.vue'),
      meta: { title: '分类管理' }
    },
    {
      path: '/seasonings',
      name: 'seasonings',
      component: () => import('../views/Seasonings.vue'),
      meta: { title: '调料管理' }
    },
    {
      path: '/inventory',
      name: 'inventory',
      component: () => import('../views/Inventory.vue'),
      meta: { title: '库存管理' }
    },
    {
      path: '/recommend',
      name: 'recommend',
      component: () => import('../views/Recommend.vue'),
      meta: { title: '智能推荐' }
    },
    {
      path: '/rag',
      name: 'rag',
      component: () => import('../views/Rag.vue'),
      meta: { title: 'AI 语义检索' }
    },
    {
      path: '/ai-collect',
      name: 'ai-collect',
      component: () => import('../views/AiCollection.vue'),
      meta: { title: 'AI 采集入库' }
    },
    {
      path: '/ingredients',
      name: 'ingredients',
      component: () => import('../views/Ingredients.vue'),
      meta: { title: '食材管理' }
    },
    {
      path: '/me',
      name: 'me',
      component: () => import('../views/Me.vue'),
      meta: { title: '我的' }
    }
  ]
});

// 路由守卫
router.beforeEach((to, from, next) => {
  document.title = `${to.meta.title || '首页'} - AI 家庭厨房助手`;
  next();
});

export default router;
