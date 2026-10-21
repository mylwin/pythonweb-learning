import http from './http'

export const addHistory = (newsId) => http.post('/api/history/add', { newsId })

export const getHistoryList = (params) => http.get('/api/history/list', { params })

export const removeHistory = (id) => http.delete(`/api/history/delete/${id}`)

export const clearHistory = () => http.delete('/api/history/clear')
