<template>
  <div class="page-comparison">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>实时发电功率 vs 预测发电功率</span>
          <div>
            <el-radio-group v-model="compHours" size="small" @change="loadComparisonData">
              <el-radio-button :value="3">3 小时</el-radio-button>
              <el-radio-button :value="6">6 小时</el-radio-button>
              <el-radio-button :value="12">12 小时</el-radio-button>
              <el-radio-button :value="24">24 小时</el-radio-button>
            </el-radio-group>
            <el-button type="primary" size="small" style="margin-left: 12px" :loading="loading" @click="loadComparisonData">
              刷新对比
            </el-button>
          </div>
        </div>
      </template>
      <div ref="comparisonChartRef" class="chart-container-lg"></div>
    </el-card>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span>偏差分析</span></template>
          <div ref="deviationChartRef" class="chart-container-sm"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span>预测精度统计</span></template>
          <div class="accuracy-stats">
            <div class="acc-item">
              <div class="acc-label">平均绝对误差 (MAE)</div>
              <div class="acc-value" :class="{ 'acc-good': parseFloat(stats.mae) < 1 }">{{ stats.mae }} kW</div>
            </div>
            <div class="acc-item">
              <div class="acc-label">均方根误差 (RMSE)</div>
              <div class="acc-value" :class="{ 'acc-good': parseFloat(stats.rmse) < 1.5 }">{{ stats.rmse }} kW</div>
            </div>
            <div class="acc-item">
              <div class="acc-label">平均绝对百分比误差 (MAPE)</div>
              <div class="acc-value" :class="{ 'acc-good': parseFloat(stats.mape) < 10 }">{{ stats.mape }}%</div>
            </div>
            <div class="acc-item">
              <div class="acc-label">预测精度</div>
              <div class="acc-value acc-good">{{ stats.accuracy }}%</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { dataAPI } from '@/utils/api'

const compHours = ref(6)
const loading = ref(false)
const comparisonChartRef = ref(null)
const deviationChartRef = ref(null)
const stats = reactive({ mae: '-', rmse: '-', mape: '-', accuracy: '-' })
let comparisonChart = null
let deviationChart = null

async function loadComparisonData() {
  loading.value = true
  try {
    const res = await dataAPI.getComparison(compHours.value)
    if (res.code === 200) {
      renderComparisonChart(res.data.actual, res.data.predicted)
      calculateStats(res.data.actual, res.data.predicted)
    }
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

function calculateStats(actual, predicted) {
  if (!actual || actual.length === 0) return
  let sumAbsErr = 0, sumSqErr = 0, sumAbsPercErr = 0, count = 0
  for (let i = 0; i < actual.length; i++) {
    const a = actual[i].active_power
    const p = predicted[i] ? predicted[i].predicted_power : a
    const diff = a - p
    sumAbsErr += Math.abs(diff)
    sumSqErr += diff * diff
    if (p > 0) {
      sumAbsPercErr += Math.abs(diff / p)
      count++
    }
  }
  const n = actual.length
  stats.mae = (sumAbsErr / n).toFixed(2)
  stats.rmse = Math.sqrt(sumSqErr / n).toFixed(2)
  stats.mape = count > 0 ? (sumAbsPercErr / count * 100).toFixed(1) : '-'
  stats.accuracy = count > 0 ? (100 - sumAbsPercErr / count * 100).toFixed(1) : '-'
}

function renderComparisonChart(actual, predicted) {
  nextTick(() => {
    const el = comparisonChartRef.value
    if (!el) return
    if (comparisonChart) comparisonChart.dispose()
    comparisonChart = echarts.init(el)

    const times = actual.map(d => d.timestamp.substring(11, 16))
    const actualPowers = actual.map(d => d.active_power)
    const predPowers = predicted.map(d => d.predicted_power)

    comparisonChart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: ['实际功率', '预测功率'] },
      grid: { left: 60, right: 30, bottom: 40, top: 50 },
      xAxis: { type: 'category', data: times, axisLabel: { interval: Math.floor(times.length / 10) } },
      yAxis: { type: 'value', name: '功率 (kW)' },
      series: [
        { name: '实际功率', type: 'line', data: actualPowers, smooth: true, itemStyle: { color: '#409eff' } },
        { name: '预测功率', type: 'line', data: predPowers, smooth: true, itemStyle: { color: '#67c23a' }, lineStyle: { type: 'dashed' } }
      ]
    })

    // Deviation chart
    const devEl = deviationChartRef.value
    if (devEl) {
      if (deviationChart) deviationChart.dispose()
      deviationChart = echarts.init(devEl)
      const deviations = actual.map((d, i) => {
        const pred = predicted[i] ? predicted[i].predicted_power : d.active_power
        return Math.round((d.active_power - pred) * 100) / 100
      })
      deviationChart.setOption({
        tooltip: { trigger: 'axis' },
        grid: { left: 60, right: 20, bottom: 30, top: 30 },
        xAxis: { type: 'category', data: times },
        yAxis: { type: 'value', name: '偏差(kW)' },
        series: [{
          type: 'bar', data: deviations,
          itemStyle: { color: params => params.value >= 0 ? '#67c23a' : '#f56c6c' }
        }]
      })
      window.addEventListener('resize', () => deviationChart.resize())
    }
    window.addEventListener('resize', () => comparisonChart.resize())
  })
}

onMounted(() => {
  loadComparisonData()
})
</script>

<style scoped lang="scss">
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
}
.chart-container-lg { height: 420px; }
.chart-container-sm { height: 300px; }
.accuracy-stats { padding: 16px 0; }
.acc-item {
  display: flex;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid #f0f0f0;
  &:last-child { border-bottom: none; }
}
.acc-label { color: #909399; font-size: 14px; }
.acc-value { font-size: 16px; font-weight: 600; color: #303133; }
.acc-good { color: #67c23a; }
</style>
