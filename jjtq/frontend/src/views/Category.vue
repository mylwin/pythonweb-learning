<template>
  <div class="category">
    <van-nav-bar
      :title="$t('common.allCategories')"
      :left-text="$t('common.back')"
      left-arrow
      @click-left="onClickLeft"
      fixed
    />

    <div class="category-container">
      <van-grid :column-num="3" :border="false">
        <van-grid-item
          v-for="category in displayCategories"
          :key="category.id"
          :text="translateCategory(t, category.name)"
          icon="newspaper-o"
          @click="goToCategoryNews(category.id)"
        />
      </van-grid>
    </div>

    <tab-bar />
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useNewsStore } from '../store/modules/news'
import TabBar from '../components/TabBar.vue'
import { translateCategory } from '../utils/category'

const newsStore = useNewsStore()
const router = useRouter()
const { t } = useI18n()

const displayCategories = computed(() => newsStore.displayCategories)

// 直接打开分类页时也要能拿到数据，不能依赖首页先加载
onMounted(() => {
  newsStore.getCategories()
})

const onClickLeft = () => {
  router.back()
}

const goToCategoryNews = (categoryId) => {
  router.push({
    path: '/home',
    query: { categoryId },
  })
}
</script>

<style scoped>
.category {
  padding-top: 46px;
  padding-bottom: 50px;
  background-color: #f7f8fa;
  min-height: 100vh;
}

.category-container {
  padding: 16px;
  background-color: #fff;
  margin-top: 12px;
  border-radius: 8px;
}

:deep(.van-grid-item__content) {
  background-color: #f5f7fa;
  border-radius: 8px;
  padding: 20px 0;
}

:deep(.van-grid-item__icon) {
  font-size: 28px;
  color: #1989fa;
}

:deep(.van-grid-item__text) {
  margin-top: 8px;
  color: #333;
  font-size: 14px;
}
</style>
