<template>
  <div class="home">
    <van-nav-bar :title="$t('home.title')" fixed />

    <!-- 更多分类入口 -->
    <div class="more-options">
      <div class="more-tab" @click="goToCategory">
        {{ $t('home.more') }} <van-icon name="arrow" />
      </div>
    </div>

    <div class="category-tabs">
      <van-tabs v-model:active="activeTab" sticky swipeable animated>
        <van-tab
          v-for="category in displayCategories"
          :key="category.id"
          :title="translateCategory(t, category.name)"
        >
          <van-pull-refresh v-model="newsStore.refreshing" @refresh="onRefresh">
            <van-list
              :loading="newsStore.loading"
              :finished="newsStore.finished"
              :finished-text="$t('home.noMore')"
              @load="onLoad"
            >
              <van-empty
                v-if="newsStore.error && !newsStore.newsList.length"
                :description="newsStore.error"
              />
              <news-item
                v-for="item in newsStore.newsList"
                :key="item.id"
                :news="item"
              />
            </van-list>
          </van-pull-refresh>
        </van-tab>
      </van-tabs>
    </div>

    <tab-bar />
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useNewsStore } from '../store/modules/news'
import NewsItem from '../components/NewsItem.vue'
import TabBar from '../components/TabBar.vue'
import { translateCategory } from '../utils/category'

const newsStore = useNewsStore()
const route = useRoute()
const router = useRouter()
const { t } = useI18n()

const activeTab = ref(0)

// 只展示真实分类，“更多”是独立入口
const displayCategories = computed(() => newsStore.displayCategories)

// 根据路由 query 选中对应分类
const applyRouteCategory = () => {
  const rawCategoryId = route.query.categoryId
  if (!rawCategoryId) return

  const categoryId = Number(rawCategoryId)
  const index = displayCategories.value.findIndex((category) => category.id === categoryId)

  if (index !== -1) {
    activeTab.value = index
  } else {
    newsStore.changeCategory(categoryId)
  }
}

watch(activeTab, (index) => {
  const category = displayCategories.value[index]
  if (!category) return
  if (newsStore.currentCategory !== category.id) {
    newsStore.changeCategory(category.id)
  }
})

watch(() => route.query.categoryId, applyRouteCategory)

onMounted(async () => {
  await newsStore.getCategories()
  applyRouteCategory()

  if (!newsStore.newsList.length && !newsStore.loading) {
    await newsStore.getNewsList(true)
  }
})

const goToCategory = () => {
  router.push('/category')
}

const onRefresh = () => {
  newsStore.getNewsList(true)
}

const onLoad = () => {
  newsStore.getNewsList()
}
</script>

<style scoped>
.home {
  padding-top: 46px;
  padding-bottom: 50px;
  background-color: #f7f8fa;
  min-height: 100vh;
}

.category-tabs {
  margin-bottom: 10px;
  position: relative;
}

:deep(.van-tabs__wrap) {
  background-color: #fff;
}

:deep(.van-tab) {
  font-size: 14px;
}

:deep(.van-tab--active) {
  font-weight: bold;
  color: #1989fa;
}

.more-options {
  position: fixed;
  right: 0;
  top: 46px;
  height: 44px;
  display: flex;
  align-items: center;
  background-color: #fff;
  padding: 0;
  border-radius: 4px 0 0 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  z-index: 1000;
}

.more-tab {
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #1989fa;
  font-weight: bold;
  height: 100%;
  padding: 0 10px;
}
</style>
