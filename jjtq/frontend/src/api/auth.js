import http from './http'

export const login = (payload) => http.post('/api/user/login', payload)

export const register = (payload) => http.post('/api/user/register', payload)

export const getProfile = () => http.get('/api/user/info')

export const updateBio = (bio) => http.put('/api/user/update', { bio })

export const updatePassword = (oldPassword, newPassword) =>
  http.put('/api/user/password', { oldPassword, newPassword })
