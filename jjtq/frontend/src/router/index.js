import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/store/user'

const routes = [
  {
    path: '/',
    redirect: '/home',
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: {
      title: '登录',
      guestOnly: true,
    },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/Register.vue'),
    meta: {
      title: '注册',
      guestOnly: true,
    },
  },
  {
    path: '/home',
    name: 'Home',
    component: () => import('@/views/Home.vue'),
    meta: {
      title: '首页',
      keepAlive: true,
    },
  },
  {
    path: '/news/detail/:id',
    name: 'NewsDetail',
    component: () => import('@/views/NewsDetail.vue'),
    meta: {
      title: '新闻详情',
    },
  },
  {
    path: '/history',
    name: 'History',
    component: () => import('@/views/History.vue'),
    meta: {
      title: '浏览历史',
      requiresAuth: true,
    },
  },
  {
    path: '/favorite',
    name: 'Favorite',
    component: () => import('@/views/Favorite.vue'),
    meta: {
      title: '我的收藏',
      requiresAuth: true,
    },
  },
  {
    path: '/category',
    name: 'Category',
    component: () => import('@/views/Category.vue'),
    meta: {
      title: '分类',
    },
  },
  {
    path: '/aichat',
    name: 'AIChat',
    component: () => import('@/views/AIChat.vue'),
    meta: {
      title: 'AI问答',
      keepAlive: true,
    },
  },
  {
    path: '/my',
    name: 'My',
    component: () => import('@/views/My.vue'),
    meta: {
      title: '我的',
      keepAlive: true,
    },
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('@/views/Profile.vue'),
    meta: {
      title: '个人信息',
      requiresAuth: true,
    },
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/Settings.vue'),
    meta: {
      title: '设置',
    },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFound.vue'),
    meta: {
      title: '页面不存在',
    },
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior(to, from, savedPosition) {
    return savedPosition || { top: 0 }
  },
})

router.beforeEach((to) => {
  const userStore = useUserStore()

  document.title = to.meta.title ? `${to.meta.title} - 掘金头条` : '掘金头条'

  // 未登录时限制访问需要登录的页面
  if (to.meta.requiresAuth && !userStore.getLoginStatus) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  // 已登录用户不再进入登录/注册页
  if (to.meta.guestOnly && userStore.getLoginStatus) {
    return { path: '/home' }
  }
})

export default router
