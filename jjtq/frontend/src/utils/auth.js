/**
 * 登录凭证的本地存取。
 * 统一在这里读写，避免各处直接操作 localStorage 导致 key 不一致。
 */
const TOKEN_KEY = 'jjtq_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export function setToken(token) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token)
  } else {
    localStorage.removeItem(TOKEN_KEY)
  }
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}
