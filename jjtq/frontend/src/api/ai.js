import { aiChatConfig } from '@/config/api'

/**
 * AI 问答目前由浏览器直连第三方服务（仅用于本地调试）。
 * 正式环境应改为请求后端 /api/ai/chat，由后端持有 Key 并转发 SSE。
 */
export function isAIConfigured() {
  return Boolean(aiChatConfig.apiKey)
}

/**
 * 以 SSE 方式流式获取 AI 回复。
 * @param {Array<{role: string, content: string}>} messages 对话历史
 * @param {{ signal?: AbortSignal, onDelta?: (delta: string, fullText: string) => void }} options
 * @returns {Promise<string>} 完整回复文本
 */
export async function streamChat(messages, { signal, onDelta } = {}) {
  const response = await fetch(aiChatConfig.apiEndpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${aiChatConfig.apiKey}`,
      'X-DashScope-SSE': 'enable',
    },
    body: JSON.stringify({
      model: aiChatConfig.model,
      messages,
      stream: true,
    }),
    signal,
  })

  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.error?.message || `AI 请求失败（HTTP ${response.status}）`)
  }

  if (!response.body) {
    throw new Error('当前浏览器不支持流式响应')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let fullText = ''

  const handleLine = (line) => {
    const trimmed = line.trim()
    if (!trimmed.startsWith('data:')) return

    const payload = trimmed.slice(5).trim()
    if (!payload || payload === '[DONE]') return

    try {
      const json = JSON.parse(payload)
      const content =
        json.choices?.[0]?.delta?.content ||
        json.output?.text ||
        json.choices?.[0]?.message?.content ||
        ''
      if (content) {
        fullText += content
        onDelta?.(content, fullText)
      }
    } catch {
      // 分片不完整时忽略，等待下一次拼接
    }
  }

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''
      lines.forEach(handleLine)
    }

    // 处理最后一段没有换行结尾的数据
    buffer += decoder.decode()
    if (buffer) handleLine(buffer)
  } finally {
    reader.releaseLock()
  }

  return fullText
}
