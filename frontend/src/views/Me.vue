<template>
  <div class="me">
    <div class="profile">
      <div class="avatar">🍳</div>
      <div>
        <h1>AI 家庭厨房助手</h1>
        <p class="subtitle">我的</p>
      </div>
    </div>

    <div class="menu-list">
      <router-link to="/favorites" class="menu-item">
        <span class="menu-icon">♥</span>
        <span class="menu-label">我的收藏</span>
        <span class="menu-arrow">›</span>
      </router-link>
      <router-link to="/history" class="menu-item">
        <span class="menu-icon">🕐</span>
        <span class="menu-label">浏览历史</span>
        <span class="menu-arrow">›</span>
      </router-link>
      <router-link to="/recycle-bin" class="menu-item">
        <span class="menu-icon">🗑</span>
        <span class="menu-label">回收站</span>
        <span class="menu-arrow">›</span>
      </router-link>
      <router-link to="/categories" class="menu-item">
        <span class="menu-icon">📁</span>
        <span class="menu-label">分类管理</span>
        <span class="menu-arrow">›</span>
      </router-link>
      <router-link to="/ingredients" class="menu-item">
        <span class="menu-icon">🥬</span>
        <span class="menu-label">食材管理</span>
        <span class="menu-arrow">›</span>
      </router-link>
      <router-link to="/seasonings" class="menu-item">
        <span class="menu-icon">🧂</span>
        <span class="menu-label">调料管理</span>
        <span class="menu-arrow">›</span>
      </router-link>
      <router-link to="/inventory" class="menu-item">
        <span class="menu-icon">📦</span>
        <span class="menu-label">库存管理</span>
        <span class="menu-arrow">›</span>
      </router-link>
      <router-link to="/recommend" class="menu-item">
        <span class="menu-icon">✨</span>
        <span class="menu-label">智能推荐</span>
        <span class="menu-arrow">›</span>
      </router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
.me { padding: 20px; }
.profile {
  display: flex; align-items: center; gap: 16px;
  background: white; border-radius: 12px; padding: 20px; margin-bottom: 16px;
}
.avatar {
  width: 56px; height: 56px; border-radius: 50%; background: #e3f2fd;
  display: flex; align-items: center; justify-content: center; font-size: 28px;
}
.profile h1 { margin: 0; font-size: 1.2rem; }
.subtitle { margin: 4px 0 0 0; color: #888; font-size: 14px; }

.menu-list { background: white; border-radius: 12px; overflow: hidden; }
.menu-item {
  display: flex; align-items: center; gap: 14px;
  padding: 16px; border-bottom: 1px solid #f0f0f0;
  text-decoration: none; color: #333;
}
.menu-icon { font-size: 18px; width: 28px; text-align: center; }
.menu-label { flex: 1; }
.menu-arrow { color: #ccc; font-size: 20px; }

@media (max-width: 767px) {
  .me { padding: 16px; }
  .profile h1 { text-align: center; }
}
</style>
