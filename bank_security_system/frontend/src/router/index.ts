import { createRouter, createWebHistory } from 'vue-router';
import HomeView from '@/views/HomeView.vue';
import Dashboard from '@/views/Dashboard.vue';

const routes = [
  { path: '/', component: HomeView },
  { 
    path: '/dashboard',
    component: Dashboard,
    meta: { requiresAuth: true }
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

// 简单的路由守卫
router.beforeEach((to) => {
  const authStore = useAuthStore();
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return '/login';
  }
});

export default router;