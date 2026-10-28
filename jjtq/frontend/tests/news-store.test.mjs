import assert from 'node:assert/strict'
import { after, before, beforeEach, test } from 'node:test'
import { createPinia, setActivePinia } from 'pinia'
import { createServer } from 'vite'

let vite
let useNewsStore
let http
let pending

// API 请求通过可控的适配器完成，以验证先后返回与分页行为。
function queueResponse(index, list) {
  const request = pending[index]
  assert.ok(request, `不存在第 ${index + 1} 个请求`)
  request.resolve({
    data: { code: 200, message: 'success', data: { list } },
    status: 200,
    statusText: 'OK',
    headers: {},
    config: request.config,
  })
}

async function waitForRequests(count) {
  for (let attempt = 0; attempt < 20 && pending.length < count; attempt++) {
    await new Promise((resolve) => setImmediate(resolve))
  }
  assert.equal(pending.length, count)
}

before(async () => {
  globalThis.localStorage = { getItem: () => null, setItem() {}, removeItem() {} }
  vite = await createServer({
    server: { middlewareMode: true, hmr: false, ws: false },
    appType: 'custom',
  })
  ;({ useNewsStore } = await vite.ssrLoadModule('/src/store/modules/news.js'))
  ;({ default: http } = await vite.ssrLoadModule('/src/api/http.js'))
})

after(async () => {
  await vite?.close()
  delete globalThis.localStorage
})

beforeEach(() => {
  setActivePinia(createPinia())
  pending = []
  http.defaults.adapter = (config) => new Promise((resolve, reject) => {
    pending.push({ config, resolve, reject })
  })
})

test('切换分类时发起新请求，并忽略晚到的旧分类响应', async () => {
  const store = useNewsStore()
  const headline = store.getNewsList()
  await waitForRequests(1)
  const social = store.changeCategory(2)
  await waitForRequests(2)
  const domestic = store.changeCategory(3)
  await waitForRequests(3)
  assert.deepEqual(pending.map((item) => item.config.params.categoryId), [1, 2, 3])
  assert.equal(store.loading, true)
  assert.deepEqual(store.newsList, [])

  queueResponse(1, [{ id: 2, title: '社会' }])
  await social
  assert.equal(store.loading, true)
  assert.deepEqual(store.newsList, [])
  queueResponse(2, [{ id: 3, title: '国内' }])
  await domestic
  queueResponse(0, [{ id: 1, title: '头条' }])
  await headline
  assert.equal(store.currentCategory, 3)
  assert.deepEqual(store.newsList, [{ id: 3, title: '国内' }])
  assert.equal(store.loading, false)
  assert.equal(store.page, 1)
})

test('分页加载期间阻止重复请求，切换分类后重置页码', async () => {
  const store = useNewsStore()
  const first = store.getNewsList()
  const duplicate = store.getNewsList()
  await waitForRequests(1)
  assert.equal(pending[0].config.params.page, 1)
  queueResponse(0, Array.from({ length: 10 }, (_, index) => ({ id: index + 1 })))
  await Promise.all([first, duplicate])
  const second = store.getNewsList()
  await waitForRequests(2)
  assert.equal(pending[1].config.params.page, 2)
  queueResponse(1, [{ id: 11 }])
  await second
  assert.equal(store.newsList.length, 11)
  assert.equal(store.finished, true)

  const changed = store.changeCategory(10)
  await waitForRequests(3)
  assert.equal(pending[2].config.params.categoryId, 10)
  assert.equal(pending[2].config.params.page, 1)
  assert.deepEqual(store.newsList, [])
  queueResponse(2, [{ id: 100 }])
  await changed
  assert.deepEqual(store.newsList, [{ id: 100 }])
})

test('旧请求失败不覆盖新分类结果，切换失败不显示旧分类', async () => {
  const store = useNewsStore()
  const old = store.getNewsList()
  await waitForRequests(1)
  const current = store.changeCategory(2)
  await waitForRequests(2)
  queueResponse(1, [{ id: 2 }])
  await current
  pending[0].reject(new Error('旧请求失败'))
  await old
  assert.equal(store.error, '')
  assert.deepEqual(store.newsList, [{ id: 2 }])

  const failing = store.changeCategory(3)
  await waitForRequests(3)
  pending[2].reject(new Error('当前请求失败'))
  await failing
  assert.equal(store.error, '当前请求失败')
  assert.deepEqual(store.newsList, [])
  assert.equal(store.loading, false)
})
