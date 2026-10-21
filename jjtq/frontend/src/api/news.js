import http from './http'

export const getCategories = () => http.get('/api/news/categories')

export const getNewsList = (params) => http.get('/api/news/list', { params })

export const getNewsDetail = (id) => http.get('/api/news/detail', { params: { id } })
