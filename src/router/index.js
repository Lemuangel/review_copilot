import { createRouter, createWebHistory } from 'vue-router';
import Analysis from '../views/view.vue';

const routes = [
  { path: '/', component: Analysis }        // 现在首页是综合分析
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

export default router;