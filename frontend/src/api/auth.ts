import apiClient from './client'

export const authApi = {
  login: (password: string) =>
    apiClient.post<{ access_token: string; token_type: string }>('/auth/login', { password }),
}
