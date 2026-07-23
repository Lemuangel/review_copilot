// src/main.js
import { createApp } from 'vue';
import App from './app.vue';
import ElementPlus from 'element-plus';
import 'element-plus/dist/index.css';

// 1. 引入刚刚建好的 router
import router from './router';

const app = createApp(App);
app.use(ElementPlus);
app.use(router);  // 2. 告诉 Vue 使用路由
app.mount('#app');