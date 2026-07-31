// src/utils/request.js
import axios from 'axios';

// 1. 创建“快递员”实例
const request = axios.create({
  baseURL: 'http://localhost:8000', // 后端的地址
  timeout: 120000, // 2分钟超时（Agent需要多次LLM调用）
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
    const data = response.data;
    // 如果返回的数据中有 code 字段，且 code === 200，则返回 data.data
    if (data && typeof data.code !== 'undefined') {
      if (data.code === 200) {
        return data.data;
      } else {
        return Promise.reject(data);
      }
    }
    // 如果没有 code 字段，直接返回 data（视为成功）
    return data;
  },
  (error) => {
    console.error('网络请求失败:', error.message);
    return Promise.reject(error);
  }
);

export default request;