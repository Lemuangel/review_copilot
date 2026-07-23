// src/api/review.js
import mockReviews from '../data.js';

// 模拟延迟
const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

// 1. 获取所有差评（供下拉选择）
export const getReviewList = async (params = {}) => {
  await delay(300);
  let result = [...mockReviews];
  // 简单分页
  const page = params.page || 1;
  const size = params.size || 100;
  const start = (page - 1) * size;
  const end = start + size;
  return {
    code: 200,
    data: result.slice(start, end),
    total: result.length
  };
};

// 2. 获取单条差评详情
export const getReviewDetail = async (id) => {
  await delay(200);
  const found = mockReviews.find(item => item.id === id);
  if (found) {
    return { code: 200, data: found };
  } else {
    throw { code: 404, message: '未找到' };
  }
};

// 3. 获取统计数据（饼图用）
export const getStatistics = async () => {
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
};

// 4. 模拟AI生成回复（打字机效果）
export const generateAIForReview = async (reviewId, type) => {
  await delay(500);
  const mock = mockReviews.find(r => r.id === reviewId);
  let text = '【AI模拟回复】根据该差评，建议您立即联系客户并提供解决方案。';
  if (mock) {
    if (type === 'reply')
    {
        text = '【AI客服回复】' + (mock.aiReply || '我们非常抱歉，会尽快处理您的反馈。');
    }
    if (type === 'suggestion')
    {
        text = '【运营诊断】' + (mock.aiSuggestion || '建议排查供应链批次问题。');
    }
  }
  return { code: 200, data: text };
};