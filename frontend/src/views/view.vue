<!-- src/views/Analysis.vue -->
<template>
  <div class="analysis-page">
    <!-- ========== 1. KPI 指标行 ========== -->
    <el-row :gutter="20" class="kpi-row">
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="kpi-item">
            <div class="kpi-label">📋 总差评数</div>
            <div class="kpi-value">{{ stats.total }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="kpi-item">
            <div class="kpi-label">⭐ 平均星级</div>
            <div class="kpi-value">{{ stats.avgStar }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="kpi-item">
            <div class="kpi-label">🔥 最高频问题</div>
            <div class="kpi-value">{{ stats.topCategory }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="kpi-item">
            <div class="kpi-label">🚨 1星差评</div>
            <div class="kpi-value">{{ stats.oneStarCount }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- ========== 2. 单条差评分析区（差评 + AI回复 上下结构） ========== -->
    <el-card shadow="hover" class="analysis-card">
      <template #header>
        <div class="card-header">
          <span>🔍 单条差评实时 AI 分析</span>
          <el-select v-model="selectedId" placeholder="选择差评" @change="onReviewChange" style="width:200px;">
            <el-option
              v-for="item in reviewOptions"
              :key="item.id"
              :label="item.id + ' - ' + item.translatedText.slice(0, 20) + '...'"
              :value="item.id"
            />
          </el-select>
          <el-button type="primary" size="small" @click="generateAI">生成 AI 回复</el-button>
        </div>
      </template>

      <!-- 差评信息（上半部分） -->
      <div v-if="currentReview" class="review-section">
        <div class="review-meta">
          <el-rate v-model="currentReview.starRating" disabled />
          <el-tag :type="getCategoryColor(currentReview.category)">{{ currentReview.category }}</el-tag>
          <el-tag v-if="currentReview.verified" type="success" size="small">已验证</el-tag>
          <el-tag v-if="currentReview.vineVoice" type="warning" size="small">Vine</el-tag>
          <span class="country">{{ currentReview.country }}</span>
        </div>
        <div class="review-text">
          <div class="original">
            <strong>买家原文：</strong>
            <p>{{ currentReview.commentText }}</p>
          </div>
          <div class="translated">
            <strong>AI 翻译：</strong>
            <p>{{ currentReview.translatedText }}</p>
          </div>
        </div>
        <div v-if="currentReview.images && currentReview.images.length" class="image-gallery">
          <el-image
            v-for="(img, idx) in currentReview.images"
            :key="idx"
            :src="img"
            fit="cover"
            class="thumbnail"
            :preview-src-list="currentReview.images"
          />
        </div>
      </div>
      <div v-else class="placeholder">请选择一条差评</div>

      <el-divider />

      <!-- ====== 区域一：AI 回复（对外，面向顾客） ====== -->
      <div class="ai-reply-section">
        <div class="section-header">
          <span class="section-title">💬 AI 客服回复（对外 · 可直接发给顾客）</span>
          <el-button type="primary" size="small" @click="generateAI" :loading="loading">
            {{ loading ? '生成中...' : '生成回复' }}
          </el-button>
        </div>
        <div v-if="aiReply" class="ai-content" v-html="formattedReply"></div>
        <div v-else class="ai-placeholder">点击“生成回复”，AI 将自动生成多语言客服话术，一键复制即可使用。</div>
        <div v-if="aiReply" style="margin-top: 10px;">
          <el-button type="success" size="small" @click="copyReply">
            <el-icon><CopyDocument /></el-icon> 复制回复
          </el-button>
        </div>
      </div>

      <!-- ====== 区域二：运营建议（对内，面向商家） ====== -->
      <div class="ai-suggestion-section">
        <div class="section-header">
          <span class="section-title">📋 运营优化建议（对内 · 商家决策参考）</span>
          <el-button type="warning" size="small" @click="generateSuggestion" :loading="loadingSuggestion">
            {{ loadingSuggestion ? '诊断中...' : '生成建议' }}
          </el-button>
        </div>
        <div v-if="aiSuggestion" class="ai-content" v-html="formattedSuggestion"></div>
        <div v-else class="ai-placeholder">点击“生成建议”，AI 将分析差评根因，给出供应链、客服、运营改进措施。</div>
        <div v-if="aiSuggestion" style="margin-top: 10px;">
          <el-button type="warning" size="small" @click="copySuggestion">
            <el-icon><CopyDocument /></el-icon> 复制建议
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- ========== 3. 宏观统计图表区（饼图 + 词云） ========== -->
    <el-row :gutter="20" class="chart-row">
      <el-col :span="12">
        <el-card shadow="hover" header="📈 差评类别分布">
          <div ref="pieChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover" header="☁️ 高频负面词云">
          <div ref="wordcloudRef" class="chart-container"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, computed } from 'vue';
import * as echarts from 'echarts';
import 'echarts-wordcloud';
import { ElMessage } from 'element-plus';
import { getStatistics, getReviewList, getReviewDetail, generateAIForReview } from '../api/review';

// ========== 状态 ==========
const stats = ref({ total: 0, avgStar: 0, topCategory: '--', oneStarCount: 0 });
const reviewOptions = ref([]);
const selectedId = ref('');
const currentReview = ref(null);
const aiReply = ref('');
const loading = ref(false);
const aiSuggestion = ref('');
const loadingSuggestion = ref(false);

const pieChartRef = ref(null);
const wordcloudRef = ref(null);
let pieChart = null;
let wordcloudChart = null;

// ========== 方法 ==========
// 类别颜色
const getCategoryColor = (category) => {
  const map = {
    '物流问题': 'warning',
    '尺码问题': 'danger',
    '颜色色差': 'primary',
    '质量问题': 'danger',
    '客服问题': 'info',
    '描述不符': 'warning',
    '包装问题': 'success',
    '综合（疑似恶意）': 'danger'
  };
  return map[category] || '';
};

// 加载所有差评列表（用于下拉选择）
const loadReviewOptions = async () => {
  const res = await getReviewList({ page: 1, size: 100 });
  reviewOptions.value = res.data || [];
  if (reviewOptions.value.length) {
    selectedId.value = reviewOptions.value[0].id;
    await loadReviewDetail(selectedId.value);
  }
};

// 加载单条差评详情
const loadReviewDetail = async (id) => {
  try {
    const res = await getReviewDetail(id);
    currentReview.value = res.data;
    aiReply.value = ''; // 切换时清空AI回复
  } catch (error) {
    ElMessage.error('加载差评失败');
  }
};

// 下拉切换
const onReviewChange = (id) => {
  loadReviewDetail(id);
};

// 生成AI回复（模拟实时）
const generateAI = async () => {
  if (!currentReview.value) return;
  loading.value = true;
  aiReply.value = '';
  try {
    const res = await generateAIForReview(currentReview.value.id, 'reply');
    const fullText = res.data;
    // 打字机效果
    let index = 0;
    const interval = setInterval(() => {
      if (index < fullText.length) {
        aiReply.value += fullText[index];
        index++;
      } else {
        clearInterval(interval);
        loading.value = false;
      }
    }, 25);
  } catch (error) {
    ElMessage.error('生成失败');
    loading.value = false;
  }
};

const generateSuggestion = async () => {
  if (!currentReview.value) return;
  loadingSuggestion.value = true;
  aiSuggestion.value = '';
  try {
    const res = await generateAIForReview(currentReview.value.id, 'suggestion');
    const fullText = res.data;
    let index = 0;
    const interval = setInterval(() => {
      if (index < fullText.length) {
        aiSuggestion.value += fullText[index];
        index++;
      } else {
        clearInterval(interval);
        loadingSuggestion.value = false;
      }
    }, 25);
  } catch (error) {
    ElMessage.error('生成建议失败');
    loadingSuggestion.value = false;
  }
};

// 格式化运营建议（换行转 <br>）
const formattedSuggestion = computed(() => {
  return aiSuggestion.value.replace(/\n/g, '<br>');
});

// 复制运营建议
const copySuggestion = () => {
  navigator.clipboard.writeText(aiSuggestion.value).then(() => {
    ElMessage.success('已复制');
  }).catch(() => {
    ElMessage.error('复制失败');
  });
};

// 复制回复
const copyReply = () => {
  navigator.clipboard.writeText(aiReply.value).then(() => {
    ElMessage.success('已复制');
  }).catch(() => {
    ElMessage.error('复制失败');
  });
};

// 格式化换行
const formattedReply = computed(() => {
  return aiReply.value.replace(/\n/g, '<br>');
});

// ========== 加载统计数据并绘制图表 ==========
const loadStatsAndCharts = async () => {
  const res = await getStatistics();
  const data = res.data;
  const total = data.total || 0;
  const starDist = data.starDistribution || [];
  const categories = data.categories || [];
  let totalStars = 0;
  let oneStar = 0;
  starDist.forEach(item => {
    totalStars += item.star * item.count;
    if (item.star === 1) oneStar = item.count;
  });
  stats.value = {
    total,
    avgStar: total > 0 ? (totalStars / total).toFixed(1) : 0,
    topCategory: categories.length ? categories.reduce((a, b) => a.value > b.value ? a : b).name : '--',
    oneStarCount: oneStar
  };

  await nextTick();
  // 饼图
  if (pieChartRef.value) {
    if (pieChart) pieChart.dispose();
    pieChart = echarts.init(pieChartRef.value);
    pieChart.setOption({
      tooltip: { trigger: 'item' },
      legend: { orient: 'vertical', left: 'left' },
      color: ['#F56C6C', '#E6A23C', '#409EFF', '#67C23A', '#909399'],
      series: [{
        type: 'pie',
        radius: '50%',
        data: categories.length ? categories : [{ name: '暂无数据', value: 1 }]
      }]
    });
    window.addEventListener('resize', () => pieChart?.resize());
  }


  if (wordcloudRef.value) {
    if (wordcloudChart) wordcloudChart.dispose();
    wordcloudChart = echarts.init(wordcloudRef.value);
    const wordCloudData = [
      { name: '物流', value: 28 }, { name: '慢', value: 25 }, { name: '丢包', value: 18 },
      { name: '尺码', value: 22 }, { name: '太小', value: 30 }, { name: '色差', value: 20 },
      { name: '质量', value: 35 }, { name: '客服', value: 15 }, { name: '退款', value: 12 },
      { name: '包装', value: 14 }, { name: '描述不符', value: 19 }, { name: '气味', value: 8 }
    ];
    wordcloudChart.setOption({
      series: [{
        type: 'wordCloud',
        gridSize: 20,
        sizeRange: [14, 60],
        rotationRange: [0, 0],
        shape: 'circle',
        data: wordCloudData,
        textStyle: {
          color: () => ['#F56C6C', '#E6A23C', '#409EFF', '#67C23A', '#9B59B6'][Math.floor(Math.random() * 5)]
        }
      }]
    });
    window.addEventListener('resize', () => wordcloudChart?.resize());
  }
};

// ========== 初始化 ==========
onMounted(async () => {
  await loadReviewOptions();
  await loadStatsAndCharts();
});
</script>

<style scoped>
.analysis-page {
  padding: 20px;
  background: #f5f7fa;
  min-height: 100vh;
}
.kpi-row {
  margin-bottom: 20px;
}
.kpi-item {
  text-align: center;
  padding: 10px 0;
}
.kpi-label {
  font-size: 14px;
  color: #909399;
}
.kpi-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
}
.analysis-card {
  margin-bottom: 20px;
}
.card-header {
  display: flex;
  align-items: center;
  gap: 15px;
  flex-wrap: wrap;
}
.card-header span {
  font-weight: bold;
  font-size: 16px;
}
.review-section {
  padding: 10px 0;
}
.review-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}
.country {
  font-weight: bold;
  color: #409EFF;
}
.review-text {
  background: #fafafa;
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 12px;
}
.review-text p {
  margin: 4px 0;
  line-height: 1.6;
}
.original p {
  color: #606266;
}
.translated p {
  font-weight: bold;
  color: #303133;
}
.image-gallery {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.thumbnail {
  width: 70px;
  height: 70px;
  border-radius: 6px;
  cursor: pointer;
}
.placeholder {
  color: #c0c4cc;
  text-align: center;
  padding: 30px 0;
}
.chart-row {
  margin-top: 20px;
}
.chart-container {
  width: 100%;
  height: 300px;
}


.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.section-title {
  font-weight: bold;
  font-size: 15px;
}

.ai-reply-section {
  padding: 16px;
  background: #f0f9ff;
  border-radius: 8px;
  border-left: 4px solid #409EFF;
  margin-bottom: 16px;
  margin-top: 10px;
}
.ai-suggestion-section {
  padding: 16px;
  background: #fef7e0;
  border-radius: 8px;
  border-left: 4px solid #E6A23C;
  margin-bottom: 10px;
}
.ai-content {
  font-size: 15px;
  line-height: 1.8;
  white-space: pre-wrap;
  min-height: 50px;
}
.ai-placeholder {
  color: #909399;
  font-style: italic;
  min-height: 40px;
  line-height: 40px;
}
</style>