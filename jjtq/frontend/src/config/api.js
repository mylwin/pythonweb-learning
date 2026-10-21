/**
 * API 配置文件
 * 所有地址都从环境变量读取，避免把地址和密钥写死在源码里。
 * 环境变量见项目根目录的 .env.example。
 */

// API 基础地址：开发环境留空，走 vite 的 /api 代理
export const apiConfig = {
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
}

export const aiChatConfig = {
  apiEndpoint:
    import.meta.env.VITE_AI_API_ENDPOINT ||
    'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions',

  // 仅本地调试使用；正式环境应由后端代理持有 Key
  apiKey: import.meta.env.VITE_AI_API_KEY || '',

  model: import.meta.env.VITE_AI_MODEL || 'qwen3-max-preview',
}
