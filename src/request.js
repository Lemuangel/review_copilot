// src/utils/request.js
import axios from 'axios';

// 1. 创建“快递员”实例
const request = axios.create({
  baseURL: 'http://localhost:8000/api', // 后端的地址
  timeout: 10000, // 10秒超时
});

// 2. “安检门”：发请求前自动加 Token
request.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
  },
  (error) => Promise.reject(error)
);

// 3. “代收点”：拿到结果后统一拆包
request.interceptors.response.use(
  (response) => {
    if (response.data.code === 200) {
      return response.data.data; // 只把真正的内容丢给页面
    } else {
      return Promise.reject(response.data);
    }
  },
  (error) => {
    console.error('网络请求失败:', error.message);
    return Promise.reject(error);
  }
);

export default request;