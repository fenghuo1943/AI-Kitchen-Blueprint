<template>
  <div class="app">
    <nav class="navbar">
      <router-link to="/" class="nav-brand">🍳 AI 厨房助手</router-link>
      <div class="nav-links">
        <router-link to="/recipes">菜谱库</router-link>
        <router-link to="/inventory">库存管理</router-link>
        <router-link to="/recommend">智能推荐</router-link>
        <router-link to="/ingredients">食材管理</router-link>
      </div>
    </nav>
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import { useAppStore } from './stores/app';

const appStore = useAppStore();

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
  z-index: 100;
}

.nav-brand {
  font-size: 1.3rem;
  font-weight: 600;
  color: #333;
  text-decoration: none;
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
}

.nav-links a:hover {
  color: #4a90d9;
}

.nav-links a.router-link-active {
  color: #4a90d9;
  font-weight: 500;
}

.main-content {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}
</style>
