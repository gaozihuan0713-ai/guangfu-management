import * as echarts from 'echarts'

const chartInstances = new Map()

export function initChart(el) {
  if (chartInstances.has(el)) {
    chartInstances.get(el).dispose()
  }
  const chart = echarts.init(el)
  chartInstances.set(el, chart)
  return chart
}

export function resizeAllCharts() {
  chartInstances.forEach(chart => chart.resize())
}

export function disposeChart(el) {
  if (chartInstances.has(el)) {
    chartInstances.get(el).dispose()
    chartInstances.delete(el)
  }
}

export function formatTime(ts, withDate = false) {
  if (!ts) return ''
  if (withDate) return ts.substring(5, 16)
  return ts.substring(11, 16)
}

export function getPowerLevel(power) {
  if (power > 80) return { label: '高功率', type: 'danger' }
  if (power > 30) return { label: '中功率', type: 'warning' }
  if (power > 5) return { label: '低功率', type: 'info' }
  return { label: '微功率', type: 'success' }
}
