const CATEGORY_KEY_MAP = {
  头条: 'headline',
  社会: 'society',
  国内: 'domestic',
  国际: 'international',
  娱乐: 'entertainment',
  体育: 'sports',
  军事: 'military',
  科技: 'technology',
  财经: 'finance',
  更多: 'more',
}

/**
 * 把后端返回的分类名翻译成当前语言。
 * @param {(key: string) => string} t vue-i18n 的 t 函数
 * @param {string} categoryName 后端分类名
 */
export function translateCategory(t, categoryName) {
  const key = CATEGORY_KEY_MAP[categoryName]
  return key ? t(`home.categories.${key}`) : categoryName
}
