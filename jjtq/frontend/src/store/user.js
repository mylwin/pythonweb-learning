import { defineStore } from 'pinia'
import * as authApi from '@/api/auth'
import { clearToken, getToken, setToken } from '@/utils/auth'

export const useUserStore = defineStore('user', {
  state: () => ({
    userInfo: null,
    token: getToken(),
    userBio: '这是我的个人简介',
  }),

  getters: {
    getUserInfo: (state) => state.userInfo,
    getToken: (state) => state.token,
    // 登录态只由 token 决定，避免 isLogin 与 token 不一致
    getLoginStatus: (state) => Boolean(state.token),
    getUserBio: (state) => state.userInfo?.bio || state.userBio,
  },

  actions: {
    setAuth(token, userInfo) {
      setToken(token)
      this.token = token || ''
      this.userInfo = userInfo || null
    },

    async login(userData) {
      try {
        const data = await authApi.login({
          username: userData.username,
          password: userData.password,
        })
        this.setAuth(data?.token, data?.userInfo)
        return { success: true, message: '登录成功' }
      } catch (error) {
        return {
          success: false,
          message: error.isAuthError ? '用户名或密码错误' : error.message || '登录失败',
        }
      }
    },

    async register(userData) {
      try {
        const data = await authApi.register({
          username: userData.username,
          password: userData.password,
        })
        this.setAuth(data?.token, data?.userInfo)
        return { success: true, message: '注册成功' }
      } catch (error) {
        return { success: false, message: error.message || '注册失败' }
      }
    },

    logout() {
      clearToken()
      this.token = ''
      this.userInfo = null
    },

    async getUserInfoDetail() {
      if (!this.token) {
        return { success: false, message: '未登录' }
      }

      try {
        const data = await authApi.getProfile()
        this.userInfo = data
        return { success: true, message: '获取用户信息成功', data }
      } catch (error) {
        if (error.isAuthError) {
          this.logout()
        }
        return { success: false, message: error.message || '获取用户信息失败' }
      }
    },

    async updateUserBio(bio) {
      if (!this.token) {
        return { success: false, message: '未登录' }
      }

      try {
        await authApi.updateBio(bio)
        this.userInfo = { ...(this.userInfo || {}), bio }
        return { success: true, message: '更新个人简介成功' }
      } catch (error) {
        return { success: false, message: error.message || '更新个人简介失败' }
      }
    },

    async updatePassword(oldPassword, newPassword) {
      if (!this.token) {
        return { success: false, message: '未登录' }
      }

      try {
        await authApi.updatePassword(oldPassword, newPassword)
        this.logout()
        return { success: true, message: '密码修改成功，请重新登录' }
      } catch (error) {
        if (error.isAuthError) this.logout()
        return { success: false, message: error.message || '密码修改失败' }
      }
    },
  },

  // 只持久化用户资料；token 由 utils/auth.js 单独管理
  persist: {
    key: 'jjtq-user',
    storage: localStorage,
    pick: ['userInfo'],
  },
})
