<template>
  <div class="page-dashboard">
    <el-row :gutter="20" class="stat-cards">
      <el-col :span="6">
        <div class="stat-card power-card">
          <div class="stat-icon"><el-icon :size="36"><Lightning /></el-icon></div>
          <div class="stat-info">
            <div class="stat-value">{{ dashboardData.current_power || 0 }} <small>kW</small></div>
            <div class="stat-label">当前发电功率</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card energy-card">
          <div class="stat-icon"><el-icon :size="36"><Coin /></el-icon></div>
          <div class="stat-info">
            <div class="stat-value">{{ dashboardData.today_energy || 0 }} <small>MWh</small></div>
            <div class="stat-label">今日发电量</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card radiation-card">
          <div class="stat-icon"><el-icon :size="36"><Sunny /></el-icon></div>
          <div class="stat-info">
            <div class="stat-value">{{ dashboardData.current_radiation || 0 }} <small>W/m²</small></div>
            <div class="stat-label">当前辐照度</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card temp-card">
          <div class="stat-icon"><el-icon :size="36"><Odometer /></el-icon></div>
          <div class="stat-info">
            <div class="stat-value">{{ dashboardData.current_temp || 0 }} <small>°C</small></div>
            <div class="stat-label">当前温度</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="chart-row">
      <el-col :span="16">
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <div class="card-header">
              <span>实时发电功率趋势</span>
              <el-radio-group v-model="realtimeHours" size="small" @change="loadRealtimeData">
                <el-radio-button :value="6">6 小时</el-radio-button>
                <el-radio-button :value="12">12 小时</el-radio-button>
                <el-radio-button :value="24">24 小时</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <div ref="realtimeChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <div class="card-header">
              <span>预测功率 (6h)</span>
            </div>
          </template>
          <div ref="predictChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="chart-row">
      <el-col :span="12">
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <div class="card-header"><span>环境监测数据</span></div>
          </template>
          <div ref="envChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <div class="card-header">
              <span>报警统计</span>
              <el-button type="primary" size="small" text @click="router.push('/alarm')">
                查看详情
              </el-button>
            </div>
          </template>
          <div class="alarm-summary">
            <div class="alarm-stat-item critical">
              <div class="alarm-num">{{ alarmStats.by_level?.critical || 0 }}</div>
              <div class="alarm-label">严重报警</div>
            </div>
            <div class="alarm-stat-item warning">
              <div class="alarm-num">{{ alarmStats.by_level?.warning || 0 }}</div>
              <div class="alarm-label">警告</div>
            </div>
            <div class="alarm-stat-item info">
              <div class="alarm-num">{{ alarmStats.by_level?.info || 0 }}</div>
              <div class="alarm-label">提示</div>
            </div>
            <div class="alarm-stat-item unacked">
              <div class="alarm-num">{{ alarmStats.by_status?.unacked || 0 }}</div>
              <div class="alarm-label">待确认</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { dataAPI, alarmAPI } from '@/utils/api'
import { Lightning, Coin, Sunny, Odometer } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const router = useRouter()
const realtimeHours = ref(24)
const realtimeChartRef = ref(null)
const predictChartRef = ref(null)
const envChartRef = ref(null)
const dashboardData = reactive({})
const alarmStats = reactive({ by_level: {}, by_status: {} })
const charts = {}

async function loadDashboard() {
  try {
    const res = await dataAPI.getDashboard()
    if (res.code === 200) {
      Object.assign(dashboardData, res.data)
    }
  } catch (e) {
    console.error('Failed to load dashboard:', e)
  }
}

async function loadRealtimeData() {
  try {
    const res = await dataAPI.getRealtime(realtimeHours.value)
    if (res.code === 200) {
      renderRealtimeChart(res.data)
      renderEnvChart(res.data)
    }
  } catch (e) {
    console.error('Failed to load realtime data:', e)
  }
}

async function loadPredictionData() {
  try {
    const res = await dataAPI.getPredict(6)
    if (res.code === 200) {
      renderPredictChart(res.data)
    }
  } catch (e) {
    console.error('Failed to load prediction data:', e)
  }
}

function renderRealtimeChart(data) {
  nextTick(() => {
    const el = realtimeChartRef.value
    if (!el) return
    if (charts.realtime) charts.realtime.dispose()
    const chart = echarts.init(el)
    charts.realtime = chart

    const times = data.map(d => d.timestamp.substring(11, 16))
    const powers = data.map(d => d.active_power)
    const radiations = data.map(d => d.radiation)

    chart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: ['发电功率', '辐照度'] },
      grid: { left: 60, right: 60, bottom: 40, top: 40 },
      xAxis: { type: 'category', data: times, axisLabel: { interval: Math.floor(times.length / 8) } },
      yAxis: [
        { type: 'value', name: '功率(kW)', position: 'left' },
        { type: 'value', name: '辐照(W/m²)', position: 'right' }
      ],
      series: [
        {
          name: '发电功率', type: 'line', data: powers, smooth: true,
          itemStyle: { color: '#409eff' }, areaStyle: { color: 'rgba(64,158,255,0.15)' }
        },
        {
          name: '辐照度', type: 'line', data: radiations, smooth: true, yAxisIndex: 1,
          itemStyle: { color: '#e6a23c' }, lineStyle: { type: 'dashed' }
        }
      ]
    })
    window.addEventListener('resize', () => chart.resize())
  })
}

function renderPredictChart(data) {
  nextTick(() => {
    const el = predictChartRef.value
    if (!el) return
    if (charts.predict) charts.predict.dispose()
    const chart = echarts.init(el)
    charts.predict = chart

    const times = data.map(d => d.timestamp.substring(11, 16))
    const powers = data.map(d => d.predicted_power)

    chart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 50, right: 20, bottom: 30, top: 20 },
      xAxis: { type: 'category', data: times },
      yAxis: { type: 'value', name: 'kW' },
      series: [{
        type: 'line', data: powers, smooth: true,
        itemStyle: { color: '#67c23a' },
        areaStyle: { color: 'rgba(103,194,58,0.2)' }
      }]
    })
    window.addEventListener('resize', () => chart.resize())
  })
}

function renderEnvChart(data) {
  nextTick(() => {
    const el = envChartRef.value
    if (!el) return
    if (charts.env) charts.env.dispose()
    const chart = echarts.init(el)
    charts.env = chart

    const times = data.map(d => d.timestamp.substring(11, 16))

    chart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: ['温度', '湿度', '风速'] },
      grid: { left: 50, right: 50, bottom: 30, top: 40 },
      xAxis: { type: 'category', data: times },
      yAxis: [
        { type: 'value', name: '°C / %' },
        { type: 'value', name: 'm/s', position: 'right' }
      ],
      series: [
        {
          name: '温度', type: 'line', data: data.map(d => d.temperature),
          smooth: true, itemStyle: { color: '#f56c6c' }
        },
        {
          name: '湿度', type: 'line', data: data.map(d => d.humidity),
          smooth: true, itemStyle: { color: '#409eff' }
        },
        {
          name: '风速', type: 'bar', data: data.map(d => d.wind_speed),
          yAxisIndex: 1, itemStyle: { color: '#67c23a' }
        }
      ]
    })
    window.addEventListener('resize', () => chart.resize())
  })
}

async function loadAlarmStats() {
  try {
    const res = await alarmAPI.getStats()
    if (res.code === 200) {
      alarmStats.by_level = res.data.by_level || {}
      alarmStats.by_status = res.data.by_status || {}
    }
  } catch (e) {
    console.error('Failed to load alarm stats:', e)
  }
}

onMounted(async () => {
  await loadDashboard()
  await loadRealtimeData()
  await loadPredictionData()
  await loadAlarmStats()
})
</script>

<style scoped lang="scss">
.stat-cards { margin-bottom: 20px; }

.stat-card {
  padding: 20px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  gap: 16px;
  color: #fff;
  position: relative;
  overflow: hidden;
  &::after {
    content: '';
    position: absolute;
    right: -20px;
    bottom: -20px;
    width: 100px;
    height: 100px;
    border-radius: 50%;
    background: rgba(255,255,255,0.1);
  }
}

.power-card { background: linear-gradient(135deg, #409eff, #337ecc); }
.energy-card { background: linear-gradient(135deg, #67c23a, #529b2e); }
.radiation-card { background: linear-gradient(135deg, #e6a23c, #cf8e24); }
.temp-card { background: linear-gradient(135deg, #f56c6c, #dd5a5a); }

.stat-icon { opacity: 0.9; }
.stat-value { font-size: 28px; font-weight: 700; line-height: 1.2; small { font-size: 14px; font-weight: 400; opacity: 0.8; } }
.stat-label { font-size: 13px; opacity: 0.85; margin-top: 4px; }

.chart-row { margin-bottom: 20px; }
.chart-card { border-radius: 8px; }

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
}

.chart-container { height: 320px; }

.alarm-summary {
  display: flex;
  justify-content: space-around;
  padding: 30px 0;
}

.alarm-stat-item { text-align: center; }
.alarm-num { font-size: 36px; font-weight: 700; line-height: 1.2; }
.alarm-label { font-size: 13px; color: #909399; margin-top: 4px; }
.alarm-stat-item.critical .alarm-num { color: #f56c6c; }
.alarm-stat-item.warning .alarm-num { color: #e6a23c; }
.alarm-stat-item.info .alarm-num { color: #409eff; }
.alarm-stat-item.unacked .alarm-num { color: #f56c6c; }
</style>
