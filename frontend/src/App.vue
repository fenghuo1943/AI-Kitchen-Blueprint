<template>
  <div class="app">
    <nav class="navbar">
      <router-link to="/" class="nav-brand">🍳 AI 厨房助手</router-link>

      <!-- 移动端汉堡菜单按钮 -->
      <button
        v-if="isMobile"
        class="menu-toggle"
        @click="toggleMobileMenu"
        :class="{ active: isMobileMenuOpen }"
      >
        <span></span>
        <span></span>
        <span></span>
      </button>

      <!-- 桌面端导航链接 -->
      <div class="nav-links" :class="{ 'mobile-open': isMobileMenuOpen }" v-if="!isMobile || isMobileMenuOpen">
        <router-link to="/recipes" @click="closeMobileMenu">菜谱库</router-link>
        <router-link to="/inventory" @click="closeMobileMenu">库存管理</router-link>
        <router-link to="/recommend" @click="closeMobileMenu">智能推荐</router-link>
        <router-link to="/ingredients" @click="closeMobileMenu">食材管理</router-link>
      </div>
    </nav>

    <!-- 移动端菜单遮罩 -->
    <div
      v-if="isMobile && isMobileMenuOpen"
      class="mobile-overlay"
      @click="closeMobileMenu"
    ></div>

    <main class="main-content" :class="{ 'has-tabbar': isMobile }">
      <router-view />
    </main>

    <!-- 移动端底部 tabbar -->
    <nav v-if="isMobile" class="tabbar">
      <router-link to="/recipes" class="tabbar-item" @click="closeMobileMenu">
        <span class="tabbar-icon">🍳</span>
        <span class="tabbar-label">菜谱库</span>
      </router-link>
      <router-link to="/menu" class="tabbar-item" @click="closeMobileMenu">
        <span class="tabbar-icon">📅</span>
        <span class="tabbar-label">菜单</span>
      </router-link>
      <router-link to="/discover" class="tabbar-item" @click="closeMobileMenu">
        <span class="tabbar-icon">✨</span>
        <span class="tabbar-label">发现</span>
      </router-link>
      <router-link to="/me" class="tabbar-item" @click="closeMobileMenu">
        <span class="tabbar-icon">👤</span>
        <span class="tabbar-label">我的</span>
      </router-link>
    </nav>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';
import { useAppStore } from './stores/app';
import { useResponsive } from './composables/useResponsive';

const appStore = useAppStore();
const { isMobile } = useResponsive();

const isMobileMenuOpen = ref(false);

function toggleMobileMenu() {
  isMobileMenuOpen.value = !isMobileMenuOpen.value;
}

function closeMobileMenu() {
  isMobileMenuOpen.value = false;
}

// 监听窗口大小变化，关闭移动端菜单
watch(isMobile, (newVal) => {
  if (!newVal) {
    isMobileMenuOpen.value = false;
  }
});

onMounted(() => {
  appStore.init();
});
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background: #f5f5f5;
  color: #333;
  line-height: 1.6;
}

.app {
  min-height: 100vh;
}

.navbar {
  background: white;
  padding: 16px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  position: sticky;
  top: 0;
  z-index: 300;
}

.nav-brand {
  font-size: 1.3rem;
  font-weight: 600;
  color: #333;
  text-decoration: none;
}

/* 移动端汉堡菜单按钮 */
.menu-toggle {
  display: none;
  flex-direction: column;
  justify-content: space-between;
  width: 30px;
  height: 21px;
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
  z-index: 200;
}

.menu-toggle span {
  display: block;
  width: 100%;
  height: 3px;
  background: #333;
  border-radius: 3px;
  transition: all 0.3s ease;
}

.menu-toggle.active span:nth-child(1) {
  transform: translateY(9px) rotate(45deg);
}

.menu-toggle.active span:nth-child(2) {
  opacity: 0;
}

.menu-toggle.active span:nth-child(3) {
  transform: translateY(-9px) rotate(-45deg);
}

.nav-links {
  display: flex;
  gap: 24px;
}

.nav-links a {
  color: #666;
  text-decoration: none;
  font-size: 14px;
  transition: color 0.2s;
  padding: 8px 0;
}

.nav-links a:hover {
  color: #4a90d9;
}

.nav-links a.router-link-active {
  color: #4a90d9;
  font-weight: 500;
}

/* 移动端菜单遮罩 */
.mobile-overlay {
  display: none;
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 150;
}

.main-content {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

/* 移动端底部 tabbar */
.tabbar {
  display: none;
}

/* 响应式样式 */
@media (max-width: 767px) {
  .navbar {
    padding: 12px 16px;
  }

  .nav-brand {
    font-size: 1.1rem;
  }

  .menu-toggle {
    display: flex;
  }

  .nav-links {
    position: fixed;
    top: 0;
    right: -280px;
    width: 280px;
    height: 100vh;
    background: white;
    flex-direction: column;
    padding: 80px 24px 24px;
    gap: 0;
    box-shadow: -2px 0 8px rgba(0, 0, 0, 0.1);
    transition: right 0.3s ease;
    z-index: 160;
  }

  .nav-links.mobile-open {
    right: 0;
  }

  .nav-links a {
    padding: 16px 0;
    border-bottom: 1px solid #eee;
    font-size: 16px;
  }

  .mobile-overlay {
    display: block;
  }

  .main-content {
    padding: 16px;
    padding-bottom: 76px; /* 为底部 tabbar 留空间 */
  }

  .main-content.has-tabbar {
    padding-bottom: 76px;
  }

  /* 底部 tabbar 样式 */
  .tabbar {
    display: flex;
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    height: 60px;
    background: white;
    border-top: 1px solid #eee;
    z-index: 200;
    box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.05);
  }

  .tabbar-item {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 2px;
    text-decoration: none;
    color: #888;
    font-size: 11px;
  }

  .tabbar-item.router-link-active {
    color: #4a90d9;
  }

  .tabbar-icon {
    font-size: 20px;
    line-height: 1;
  }
}

/* 平板端样式 */
@media (min-width: 768px) and (max-width: 1023px) {
  .nav-links {
    gap: 16px;
  }

  .nav-links a {
    font-size: 13px;
  }
}
</style>
