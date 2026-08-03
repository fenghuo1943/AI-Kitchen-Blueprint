<template>
  <div class="home">
    <h1>🍳 AI 家庭厨房助手</h1>
    <p class="subtitle">让每一餐都美味可口</p>

    <div class="features">
      <router-link to="/recipes" class="feature-card">
        <div class="feature-icon">📚</div>
        <h3>菜谱库</h3>
        <p>浏览和管理您的菜谱收藏</p>
      </router-link>

      <router-link to="/inventory" class="feature-card">
        <div class="feature-icon">🥬</div>
        <h3>库存管理</h3>
        <p>追踪食材库存和保质期</p>
      </router-link>

      <router-link to="/recommend" class="feature-card">
        <div class="feature-icon">✨</div>
        <h3>智能推荐</h3>
        <p>根据现有食材推荐菜谱</p>
      </router-link>

      <router-link to="/ingredients" class="feature-card">
        <div class="feature-icon">🧅</div>
        <h3>食材管理</h3>
        <p>管理食材信息和别名</p>
      </router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
.home {
  text-align: center;
  padding: 40px 20px;
}

h1 {
  font-size: 2.5rem;
  margin-bottom: 10px;
  color: #333;
}

.subtitle {
  font-size: 1.2rem;
  color: #666;
  margin-bottom: 40px;
}

.features {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  max-width: 800px;
  margin: 0 auto;
}

.feature-card {
  background: white;
  border-radius: 12px;
  padding: 30px 20px;
  text-decoration: none;
  color: inherit;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s, box-shadow 0.2s;
}

.feature-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
}

.feature-icon {
  font-size: 3rem;
  margin-bottom: 15px;
}

.feature-card h3 {
  margin: 0 0 10px 0;
  color: #333;
}

.feature-card p {
  margin: 0;
  color: #666;
  font-size: 0.9rem;
}
</style>
