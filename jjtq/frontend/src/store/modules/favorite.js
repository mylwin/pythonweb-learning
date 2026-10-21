import { defineStore } from 'pinia'
import * as favoriteApi from '@/api/favorite'
import { useUserStore } from '../user'

const STORAGE_KEY = 'jjtq_favorites'

function readStorage() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    return saved ? JSON.parse(saved) : []
  } catch {
    return []
  }
}

export const useFavoriteStore = defineStore('favorite', {
  state: () => ({
    favorites: readStorage(),
    loading: false,
  }),

  getters: {
    getFavorites: (state) => state.favorites,
    isFavorite: (state) => (id) => state.favorites.some((item) => item.id === id),
  },

  actions: {
    isLoggedIn() {
      return useUserStore().getLoginStatus
    },

    async checkFavoriteStatusApi(newsId) {
      if (!this.isLoggedIn()) {
        return { success: true, isFavorite: this.isFavorite(newsId), isLocal: true }
      }

      try {
        const data = await favoriteApi.checkFavorite(newsId)
        return { success: true, isFavorite: Boolean(data?.isFavorite) }
      } catch {
        // 接口不可用时回退到本地状态
        return { success: true, isFavorite: this.isFavorite(newsId), isLocal: true }
      }
    },

    async addFavoriteApi(newsId) {
      if (!this.isLoggedIn()) {
        return { success: false, message: '请先登录' }
      }

      try {
        const data = await favoriteApi.addFavorite(newsId)
        return { success: true, data }
      } catch (error) {
        return { success: false, message: error.message || '收藏失败' }
      }
    },

    async removeFavoriteApi(newsId) {
      if (!this.isLoggedIn()) {
        return { success: false, message: '请先登录' }
      }

      try {
        await favoriteApi.removeFavorite(newsId)
        return { success: true }
      } catch (error) {
        return { success: false, message: error.message || '取消收藏失败' }
      }
    },

    addFavorite(news) {
      if (!news?.id || this.isFavorite(news.id)) return

      this.favorites.unshift({
        ...news,
        favoriteTime: new Date().toLocaleString(),
      })
      this.saveFavorites()
    },

    removeFavorite(id) {
      this.favorites = this.favorites.filter((item) => item.id !== id)
      this.saveFavorites()
    },

    async toggleFavorite(news) {
      if (!news?.id) {
        return null
      }

      if (this.isFavorite(news.id)) {
        const result = await this.removeFavoriteApi(news.id)
        if (!result.success) return null
        this.removeFavorite(news.id)
        return false
      }

      const result = await this.addFavoriteApi(news.id)
      if (!result.success) return null
      this.addFavorite(news)
      return true
    },

    clearFavorites() {
      this.favorites = []
      this.saveFavorites()
    },

    async clearFavoritesApi() {
      if (!this.isLoggedIn()) {
        return { success: false, message: '请先登录' }
      }

      try {
        await favoriteApi.clearFavorites()
        this.clearFavorites()
        return { success: true }
      } catch (error) {
        return { success: false, message: error.message || '清空收藏失败' }
      }
    },

    saveFavorites() {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this.favorites))
    },

    loadFavorites() {
      this.favorites = readStorage()
    },

    async getFavoriteListApi(page = 1, pageSize = 10) {
      if (!this.isLoggedIn()) {
        return { success: false, message: '请先登录' }
      }

      this.loading = true
      try {
        const data = await favoriteApi.getFavoriteList({ page, pageSize })
        this.favorites = data?.list || []
        return { success: true, data }
      } catch (error) {
        return { success: false, message: error.message || '获取收藏列表失败' }
      } finally {
        this.loading = false
      }
    },
  },
})
