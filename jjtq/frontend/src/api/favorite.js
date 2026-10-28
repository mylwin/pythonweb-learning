import http from './http'

export const checkFavorite = (newsId) =>
  http.get('/api/favorite/check', { params: { newsId } })

export const addFavorite = (newsId) => http.post('/api/favorite/add', null, { params: { newsId } })

export const removeFavorite = (newsId) =>
  http.delete('/api/favorite/remove', { params: { newsId } })

export const clearFavorites = () => http.delete('/api/favorite/clear')

export const getFavoriteList = (params) => http.get('/api/favorite/list', { params })
