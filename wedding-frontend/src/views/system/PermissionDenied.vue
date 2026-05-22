<template>
  <div class="permission-denied">
    <div class="container">
      <div class="icon">
        <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <circle cx="12" cy="12" r="10" />
          <line x1="4.93" y1="4.93" x2="19.07" y2="19.07" />
        </svg>
      </div>
      <h1>权限不足</h1>
      <p>抱歉，您没有访问此页面的权限。</p>
      <p class="hint">如有疑问，请联系管理员。</p>
      <button class="back-btn" @click="goHome">返回首页</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

function goHome() {
  router.push('/dashboard')
}
</script>

<style scoped>
.permission-denied {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background-color: #f5f5f5;
}

.container {
  text-align: center;
  padding: 40px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  max-width: 400px;
}

.icon {
  color: #e74c3c;
  margin-bottom: 20px;
}

h1 {
  margin: 0 0 16px;
  font-size: 24px;
  color: #333;
}

p {
  margin: 0 0 8px;
  color: #666;
}

.hint {
  font-size: 14px;
  color: #999;
  margin-bottom: 24px;
}

.back-btn {
  padding: 10px 24px;
  background-color: #1890ff;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.back-btn:hover {
  background-color: #40a9ff;
}
</style>