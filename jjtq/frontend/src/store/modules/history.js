import { defineStore } from 'pinia'
import * as historyApi from '@/api/history'
import { useUserStore } from '../user'

const STORAGE_KEY = 'jjtq_history'
const MAX_ITEMS = 50

function readStorage() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    return saved ? JSON.parse(saved) : []
  } catch {
    return []
  }
}

export const useHistoryStore = defineStore('history', {
  state: () => ({
    history: readStorage(),
    loading: false,
  }),

  getters: {
    getHistory: (state) => state.history,
  },

  actions: {
    isLoggedIn() {
      return useUserStore().getLoginStatus
    },

    // 已登录时同步到后端；未登录只保留本地记录
    async addHistoryApi(newsId) {
      if (!this.isLoggedIn()) {
        return { success: false, message: '请先登录' }
      }

      try {
        const data = await historyApi.addHistory(newsId)
        return { success: true, data }
      } catch (error) {
        return { success: false, message: error.message || '添加浏览历史失败' }
      }
    },

    addHistory(news) {
      const existingIndex = this.history.findIndex((item) => item.id === news.id)
      if (existingIndex !== -1) {
        this.history.splice(existingIndex, 1)
      }

      this.history.unshift({
        ...news,
        viewTime: new Date().toLocaleString(),
      })

      if (this.history.length > MAX_ITEMS) {
        this.history.pop()
      }

      this.saveHistory()
    },

    clearHistory() {
      this.history = []
      this.saveHistory()
    },

    async clearHistoryApi() {
      if (!this.isLoggedIn()) {
        this.clearHistory()
        return { success: true, isLocal: true }
      }

      try {
        await historyApi.clearHistory()
        this.clearHistory()
        return { success: true }
      } catch (error) {
        return { success: false, message: error.message || '清空浏览历史失败' }
      }
    },

    removeHistory(id) {
      this.history = this.history.filter((item) => item.id !== id)
      this.saveHistory()
    },

    async removeHistoryApi(id) {
      if (!this.isLoggedIn()) {
        this.removeHistory(id)
        return { success: true, isLocal: true }
      }

      try {
        await historyApi.removeHistory(id)
        this.removeHistory(id)
        return { success: true }
      } catch (error) {
        return { success: false, message: error.message || '删除浏览历史失败' }
      }
    },

    saveHistory() {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this.history))
    },

    loadHistory() {
      this.history = readStorage()
    },

    async getHistoryListApi() {
      if (!this.isLoggedIn()) {
        return { success: false, message: '请先登录', isLocal: true }
      }

      this.loading = true
      try {
        const data = await historyApi.getHistoryList()
        const list = data?.list || []
        this.history = list
        this.saveHistory()
        return { success: true, data: list }
      } catch (error) {
        return { success: false, message: error.message || '获取浏览历史失败' }
      } finally {
        this.loading = false
      }
    },
  },
})
