import mockReviews from '../data.js';
import request from '../request.js';

// ========== 模式开关 ==========
const USE_MOCK = false;  // 👈 开发时用 true（读 data.js），联调时改为 false（调后端接口）

// ========== 模拟延迟（仅模拟模式使用） ==========
const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

// ============================================================
// 1. 获取差评列表
export const getReviewList = async (params = {}) => {
  if (USE_MOCK) {
    await delay(300);
    let result = [...mockReviews];
    const page = params.page || 1;
    const size = params.size || 100;
    const start = (page - 1) * size;
    const end = start + size;
    return {
      code: 200,
      data: result.slice(start, end),
      total: result.length
    };
  }
  // 真实模式：调用后端接口
  const res = await request.get('/reviews', { params });
  return res;
}

// 2. 获取单条差评详情

export const getReviewDetail = async (id) => {
  if (USE_MOCK) {
    await delay(200);
    const found = mockReviews.find(item => item.id === id);
    if (found) {
      return { code: 200, data: found };
    } else {
      throw { code: 404, message: '未找到' };
    }
  }
  const res = await request.get(`/reviews/${id}`);
  return res;
};

// ============================================================
// 3. 获取统计数据（饼图/KPI）
// ============================================================
export const getStatistics = async () => {
  if (USE_MOCK) {
    await delay(200);
    const categories = {};
    const starDistribution = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 };
    mockReviews.forEach(item => {
      categories[item.category] = (categories[item.category] || 0) + 1;
      starDistribution[item.starRating] = (starDistribution[item.starRating] || 0) + 1;
    });
    return {
      code: 200,
      data: {
        total: mockReviews.length,
        categories: Object.keys(categories).map(key => ({ name: key, value: categories[key] })),
        starDistribution: Object.keys(starDistribution).map(key => ({ star: Number(key), count: starDistribution[key] }))
      }
    };
  }
  const res = await request.get('/statistics');
  return res;
};

// ============================================================
// 4. AI 生成（回复 / 建议）
// ============================================================
export const generateAIForReview = async (reviewId, type) => {
  if (USE_MOCK) {
    await delay(500);
    const mock = mockReviews.find(r => r.id === reviewId);
    let text = '【AI模拟回复】根据该差评，建议您立即联系客户并提供解决方案。';
    if (mock) {
      if (type === 'reply') {
        text = '【AI客服回复】' + (mock.aiReply || '我们非常抱歉，会尽快处理您的反馈。');
      }
      if (type === 'suggestion') {
        text = mock.aiSuggestion || '建议排查供应链批次问题。';
      }
    }
    return { code: 200, data: text };
  }
  // 真实模式：调用后端 AI 生成接口（具体路径以后端实际为准）
  const res = await request.post('/generate', { reviewId, type });
  return res;
};

export const uploadCSV = async (file) => {
  if (USE_MOCK) {
    throw new Error('当前为模拟模式（USE_MOCK=true），请切换为 false 后再上传真实数据');
  }
  
  const formData = new FormData();
  formData.append('file', file);
  
  const res = await request.post('/reviews/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return res;
};
