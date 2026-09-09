import request from '@/utils/request'

export function loginApi(username, password) {
  const params = new URLSearchParams()
  params.append('username', username)
  params.append('password', password)

  return request.post('/auth/login', params, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
  })
}

export function logoutApi() {
  return request.post('/auth/logout')
}

export function registerApi(username, password) {
  return request.post('/auth/register', {
    username: username,
    password: password,
    status: 'enable',
    type: 'normal',
    sub_user_limit: 5
  })
}
