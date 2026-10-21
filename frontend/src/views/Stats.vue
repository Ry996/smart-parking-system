<template>
  <div class="stats-page">
  <el-card shadow="hover">
    <template #header>
      <div class="header-row">
        <div class="header-title">
          <el-icon><TrendCharts /></el-icon>
          <span>数据统计分析</span>
        </div>
        <el-radio-group v-model="period" @change="loadData">
          <el-radio-button value="day">今日</el-radio-button>
          <el-radio-button value="week">近 7 天</el-radio-button>
          <el-radio-button value="month">本月</el-radio-button>
        </el-radio-group>
      </div>
    </template>

    <el-row :gutter="20">
      <el-col :xs="24" :lg="12">
        <div ref="flowChartRef" class="chart-box"></div>
      </el-col>
      <el-col :xs="24" :lg="12">
        <div ref="incomeChartRef" class="chart-box"></div>
      </el-col>
    </el-row>
  </el-card>

  <el-card shadow="hover" class="ai-card">
    <template #header>
      <div class="header-row">
        <div class="header-title">
          <el-icon><Cpu /></el-icon>
          <span>AI 运营分析建议</span>
        </div>
        <el-button type="primary" :loading="aiLoading" @click="loadAiAdvice">
          生成 AI 建议
        </el-button>
      </div>
    </template>

    <div v-if="aiAdvice" class="ai-content">
      <el-tag :type="aiProvider === 'deepseek' ? 'success' : 'warning'">
        {{ aiProvider === 'deepseek' ? 'DeepSeek 生成' : '本地兜底建议' }}
      </el-tag>
      <div class="advice-text">{{ aiAdvice }}</div>
    </div>
    <el-empty v-else description="点击按钮，根据当前统计数据生成运营建议" />
  </el-card>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import * as echarts from 'echarts'
import { getAiAdvice, getFlowStats, getIncomeStats } from '../api'

const period = ref('week')
const flowChartRef = ref(null)
const incomeChartRef = ref(null)
const aiAdvice = ref('')
const aiProvider = ref('')
const aiLoading = ref(false)
let flowChart
let incomeChart

const loadData = async () => {
  aiAdvice.value = ''
  aiProvider.value = ''
  const [flowRes, incomeRes] = await Promise.all([
    getFlowStats({ period: period.value }),
    getIncomeStats({ period: period.value }),
  ])

  if (flowRes.code === 200) {
    flowChart.setOption({
      title: { text: '车流量统计', left: 'center', textStyle: { color: '#e2e8f0' } },
      tooltip: { trigger: 'axis', backgroundColor: '#1e293b', textStyle: { color: '#e2e8f0' } },
      legend: { textStyle: { color: '#94a3b8' } },
      xAxis: { type: 'category', data: flowRes.data.labels, axisLabel: { color: '#94a3b8' }, axisLine: { lineStyle: { color: '#334155' } } },
      yAxis: { type: 'value', name: '车次', nameTextStyle: { color: '#94a3b8' }, axisLabel: { color: '#94a3b8' }, splitLine: { lineStyle: { color: 'rgba(148,163,184,0.12)' } } },
      series: [{ type: period.value === 'day' ? 'bar' : 'line', smooth: true, data: flowRes.data.counts, itemStyle: { color: '#38bdf8' }, lineStyle: { width: 3 } }],
      grid: { top: 60, right: 20, bottom: 30, left: 50 },
    })
  }

  if (incomeRes.code === 200) {
    incomeChart.setOption({
      title: { text: '收入统计', left: 'center', textStyle: { color: '#e2e8f0' } },
      tooltip: { trigger: 'axis', backgroundColor: '#1e293b', textStyle: { color: '#e2e8f0' } },
      legend: { textStyle: { color: '#94a3b8' } },
      xAxis: { type: 'category', data: incomeRes.data.labels, axisLabel: { color: '#94a3b8' }, axisLine: { lineStyle: { color: '#334155' } } },
      yAxis: { type: 'value', name: '金额', nameTextStyle: { color: '#94a3b8' }, axisLabel: { color: '#94a3b8' }, splitLine: { lineStyle: { color: 'rgba(148,163,184,0.12)' } } },
      series: [{ type: period.value === 'day' ? 'bar' : 'line', smooth: true, data: incomeRes.data.incomes, itemStyle: { color: '#f59e0b' }, lineStyle: { width: 3 } }],
      grid: { top: 60, right: 20, bottom: 30, left: 50 },
    })
  }
}

const loadAiAdvice = async () => {
  aiLoading.value = true
  try {
    const res = await getAiAdvice({ period: period.value })
    if (res.code === 200) {
      aiAdvice.value = res.data.advice
      aiProvider.value = res.data.provider
    }
  } finally {
    aiLoading.value = false
  }
}

const resizeHandler = () => {
  flowChart?.resize()
  incomeChart?.resize()
}

onMounted(async () => {
  flowChart = echarts.init(flowChartRef.value)
  incomeChart = echarts.init(incomeChartRef.value)
  await loadData()
  window.addEventListener('resize', resizeHandler)
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeHandler)
  flowChart?.dispose()
  incomeChart?.dispose()
})
</script>

<style scoped>
.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.chart-box {
  height: 340px;
}

.ai-card {
  margin-top: 20px;
}

.ai-content {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.advice-text {
  white-space: pre-line;
  line-height: 1.8;
  color: var(--text-2);
}
</style>
