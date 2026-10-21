import { createI18n } from 'vue-i18n'
import zhCN from './locales/zh-CN.js'
import enUS from './locales/en-US.js'

const SUPPORTED_LOCALES = ['zh-CN', 'en-US']

function resolveLocale() {
  const saved = localStorage.getItem('language')
  return SUPPORTED_LOCALES.includes(saved) ? saved : 'zh-CN'
}

// 创建i18n实例
export function setupI18n() {
  const locale = resolveLocale()
  document.documentElement.setAttribute('lang', locale)

  return createI18n({
    legacy: false, // 使用组合式API
    locale,
    fallbackLocale: 'zh-CN',
    messages: {
      'zh-CN': zhCN,
      'en-US': enUS,
    },
  })
}

// 动态切换语言并同步 <html lang>
export function setI18nLanguage(i18n, locale) {
  if (i18n.mode === 'legacy') {
    i18n.global.locale = locale
  } else {
    i18n.global.locale.value = locale
  }
  document.documentElement.setAttribute('lang', locale)
}
