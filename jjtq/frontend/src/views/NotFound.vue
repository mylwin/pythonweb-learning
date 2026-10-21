<template>
  <div class="not-found">
    <van-nav-bar title="页面不存在" fixed />
    <div class="not-found-content">
      <van-empty description="你访问的页面不存在或已被移除" />
      <van-button type="primary" round @click="goHome">返回首页</van-button>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

const goHome = () => {
  router.replace('/home')
}
</script>

<style scoped>
.not-found {
  min-height: 100vh;
  padding-top: 46px;
  background-color: var(--background-color);
}

.not-found-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 32px 16px;
}
</style>
