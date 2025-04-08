import { defineStore } from 'pinia';
import { ref } from 'vue';

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '');
  const isAuthenticated = computed(() => !!token.value);

  function login(newToken: string) {
    token.value = newToken;
    localStorage.setItem('token', newToken);
  }

  function logout() {
    token.value = '';
    localStorage.removeItem('token');
  }

  return { token, isAuthenticated, login, logout };
});