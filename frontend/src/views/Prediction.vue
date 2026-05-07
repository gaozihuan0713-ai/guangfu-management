<template>
  <div class="page-prediction">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>DLinear 模型发电预测</span>
          <div>
            <el-radio-group v-model="predHours" size="small" @change="loadPredictionData">
              <el-radio-button :value="1">1 小时</el-radio-button>
              <el-radio-button :value="3">3 小时</el-radio-button>
              <el-radio-button :value="6">6 小时</el-radio-button>
              <el-radio-button :value="12">12 小时</el-radio-button>
            </el-radio-group>
            <el-button type="primary" size="small" style="margin-left: 12px" :loading="loading" @click="loadPredictionData">
              刷新预测
            </el-button>
          </div>
        </div>
      </template>
      <div ref="chartRef" class="chart-container-lg"></div>
    </el-card>

    <el-card shadow="hover" style="margin-top: 20px">
      <template #header>
        <div class="card-header">
          <span>预测详情数据</span>
          <el-button type="primary" size="small" text @click="loadPredictionData">
            <el-icon><Refresh /></el-icon> 刷新
          </el-button>
        </div>
      </template>
      <el-table :data="tableData" stripe style="width: 100%">
        <el-table-column prop="timestamp" label="预测时间" width="200" />
        <el-table-column prop="predicted_power" label="预测功率 (kW)" width="160">
          <template #default="{ row }">
            <span :class="getPowerClass(row.predicted_power)">{{ row.predicted_power }}</span>
          </template>
        </el-table-column>
        <el-table-column label="功率等级" width="120">
          <template #default="{ row }">
            <el-tag :type="getPowerLevel(row.predicted_power).type" size="small">
              {{ getPowerLevel(row.predicted_power).label }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { dataAPI } from '@/utils/api'
import { Refresh } from '@element-plus/icons-vue'

const predHours = ref(6)
const loading = ref(false)
const chartRef = ref(null)
const tableData = ref([])
let chart = null

function getPowerLevel(power) {
  if (power > 80) return { label: '高功率', type: 'danger' }
  if (power > 30) return { label: '中功率', type: 'warning' }
  if (power > 5) return { label: '低功率', type: 'info' }
  return { label: '微功率', type: 'success' }
}

function getPowerClass(power) {
  if (power > 50) return 'power-high'
  if (power < 10) return 'power-low'
  return ''
}

async function loadPredictionData() {
  loading.value = true
  try {
    const res = await dataAPI.getPredict(predHours.value)
    if (res.code === 200) {
      tableData.value = res.data
      renderChart(res.data)
    }
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

function renderChart(data) {
  nextTick(() => {
    const el = chartRef.value
    if (!el) return
    if (chart) chart.dispose()
    chart = echarts.init(el)

    const times = data.map(d => d.timestamp.substring(5, 16))
    const powers = data.map(d => d.predicted_power)

    chart.setOption({
      tooltip: { trigger: 'axis', formatter: params => {
        const p = params[0]
        return `${p.axisValue}<br/>预测功率: <b>${p.value} kW</b>`
      }},
      grid: { left: 60, right: 30, bottom: 40, top: 40 },
      xAxis: { type: 'category', data: times, axisLabel: { rotate: 30 } },
      yAxis: { type: 'value', name: '功率 (kW)' },
      series: [{
        type: 'line', data: powers, smooth: true,
        itemStyle: { color: '#409eff' },
        areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(64,158,255,0.3)' },
          { offset: 1, color: 'rgba(64,158,255,0.02)' }
        ])},
        markPoint: { data: [{ type: 'max', name: '最大值' }, { type: 'min', name: '最小值' }] },
        markLine: { data: [{ type: 'average', name: '平均值' }] }
      }]
    })
    window.addEventListener('resize', () => chart.resize())
  })
}

onMounted(() => {
  loadPredictionData()
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
.power-high { color: #f56c6c; font-weight: 600; }
.power-low { color: #909399; }
</style>
