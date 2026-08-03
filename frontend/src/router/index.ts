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
      path: '/recipes/:id',
      name: 'recipe-detail',
      component: () => import('../views/RecipeDetail.vue'),
      meta: { title: '菜谱详情' }
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
      path: '/ingredients',
      name: 'ingredients',
      component: () => import('../views/Ingredients.vue'),
      meta: { title: '食材管理' }
    }
  ]
});

// 路由守卫
router.beforeEach((to, from, next) => {
  document.title = `${to.meta.title || '首页'} - AI 家庭厨房助手`;
  next();
});

export default router;
