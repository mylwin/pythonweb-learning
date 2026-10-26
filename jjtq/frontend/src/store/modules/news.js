import { defineStore } from 'pinia'
import * as newsApi from '@/api/news'

const PAGE_SIZE = 10
const MORE_CATEGORY_ID = 10
const MORE_CATEGORY_NAME = '更多'

const FALLBACK_CATEGORIES = [
  { id: 1, name: '头条' },
  { id: 2, name: '社会' },
  { id: 3, name: '国内' },
  { id: 4, name: '国际' },
  { id: 5, name: '娱乐' },
  { id: 6, name: '体育' },
  { id: 7, name: '科技' },
]

// 按 id 去重，避免分页并发时同一篇新闻进入列表两次
function mergeUnique(existing, incoming) {
  const seen = new Set(existing.map((item) => item.id))
  const merged = [...existing]
  for (const item of incoming) {
    if (!seen.has(item.id)) {
      seen.add(item.id)
      merged.push(item)
    }
  }
  return merged
}

export const useNewsStore = defineStore('news', {
  state: () => ({
    newsList: [],
    newsDetail: {},
    categories: [],
    currentCategory: 1,
    page: 0,
    loading: false,
    refreshing: false,
    finished: false,
    categoriesLoading: false,
    detailRequestId: 0,
    error: '',
  }),

  getters: {
    // 首页/分类页只展示真实分类，“更多”是独立入口
    displayCategories: (state) =>
      state.categories.filter((category) => category.name !== MORE_CATEGORY_NAME),
    moreCategoryId: () => MORE_CATEGORY_ID,
  },

  actions: {
    async getCategories() {
      if (this.categoriesLoading || this.categories.length) return

      this.categoriesLoading = true
      try {
        const data = await newsApi.getCategories()
        const list = Array.isArray(data) ? data : data?.list || []
        this.categories = [...list, { id: MORE_CATEGORY_ID, name: MORE_CATEGORY_NAME }]
      } catch (error) {
        this.error = error.message || '获取新闻分类失败'
        this.categories = [
          ...FALLBACK_CATEGORIES,
          { id: MORE_CATEGORY_ID, name: MORE_CATEGORY_NAME },
        ]
      } finally {
        if (!this.currentCategory && this.categories.length) {
          this.currentCategory = this.categories[0].id
        }
        this.categoriesLoading = false
      }
    },

    changeCategory(categoryId) {
      if (categoryId === MORE_CATEGORY_ID) return
      if (this.currentCategory === categoryId && this.newsList.length) return

      this.currentCategory = categoryId
      this.getNewsList(true)
    },

    async getNewsList(isRefresh = false) {
      // 同一个列表同时只允许一个请求，避免 van-list 重复触发
      if (this.loading) return

      if (isRefresh) {
        this.refreshing = true
        this.page = 0
        this.finished = false
      }

      this.loading = true
      this.error = ''

      const page = isRefresh ? 1 : this.page + 1

      try {
        const data = await newsApi.getNewsList({
          categoryId: this.currentCategory,
          page,
          pageSize: PAGE_SIZE,
        })

        const list = data?.list || []
        this.newsList = isRefresh ? list : mergeUnique(this.newsList, list)
        this.page = page
        this.finished = list.length < PAGE_SIZE
      } catch (error) {
        this.error = error.message || '获取新闻列表失败'
        // 刷新失败时保留旧数据，避免页面变空
        if (isRefresh) {
          this.finished = false
        }
      } finally {
        this.loading = false
        this.refreshing = false
      }
    },

    async getNewsDetail(id) {
      const requestId = ++this.detailRequestId
      this.newsDetail = {}
      this.error = ''

      try {
        const data = await newsApi.getNewsDetail(id)
        // 防止快速切换详情时旧请求覆盖新数据
        if (requestId !== this.detailRequestId) {
          return { success: false, stale: true }
        }
        if (!data || Number(data.id) !== Number(id)) {
          throw new Error('新闻详情数据不匹配')
        }
        this.newsDetail = data
        return { success: true }
      } catch (error) {
        if (requestId !== this.detailRequestId) {
          return { success: false, stale: true }
        }
        this.error = error.message || '获取新闻详情失败'
        return { success: false, message: this.error }
      }
    },

    getCategoryName(categoryId) {
      const category = this.categories.find((item) => item.id === categoryId)
      return category ? category.name : '未知'
    },
  },
})
