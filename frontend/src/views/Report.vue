<template>
  <div class="page-report">
    <el-card shadow="hover">
      <template #header>
        <span>数据导出</span>
      </template>
      <el-form :model="form" label-width="120px" class="export-form">
        <el-form-item label="报表类型">
          <el-select v-model="form.type" style="width: 100%">
            <el-option label="历史数据报表" value="history"></el-option>
            <el-option label="预测对比报表" value="comparison"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker v-model="form.start_date" type="date" placeholder="选择开始日期" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker v-model="form.end_date" type="date" placeholder="选择结束日期" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="exportLoading" @click="handleExport">
            <el-icon><Download /></el-icon> 导出CSV
          </el-button>
          <el-button @click="previewReport" :loading="previewLoading">
            <el-icon><View /></el-icon> 预览数据
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card v-if="previewData.length > 0" shadow="hover" style="margin-top: 20px">
      <template #header>
        <span>数据预览 (共 {{ total }} 条)</span>
      </template>
      <el-table :data="previewData" stripe max-height="400">
        <el-table-column v-for="col in columns" :key="col.prop" :prop="col.prop" :label="col.label" :width="col.width" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { dataAPI } from '@/utils/api'
import { Download, View } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const form = reactive({
  type: 'history',
  start_date: '',
  end_date: ''
})
const exportLoading = ref(false)
const previewLoading = ref(false)
const previewData = ref([])
const total = ref(0)

const columns = [
  { prop: 'timestamp', label: '时间', width: 180 },
  { prop: 'active_power', label: '功率(kW)', width: 120 },
  { prop: 'radiation', label: '辐照(W/m²)', width: 130 },
  { prop: 'temperature', label: '温度(°C)', width: 100 },
  { prop: 'humidity', label: '湿度(%)', width: 100 },
  { prop: 'wind_speed', label: '风速(m/s)', width: 100 }
]

async function handleExport() {
  exportLoading.value = true
  try {
    const res = await dataAPI.exportData(form)
    const blob = new Blob([res], { type: 'text/csv;charset=utf-8;' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `solar_${form.type}_${form.start_date || 'all'}_${form.end_date || 'all'}.csv`
    a.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (e) {
    ElMessage.error('导出失败')
  } finally {
    exportLoading.value = false
  }
}

async function previewReport() {
  previewLoading.value = true
  try {
    const res = await dataAPI.getHistory({ page: 1, per_page: 50, start_date: form.start_date, end_date: form.end_date })
    if (res.code === 200) {
      previewData.value = res.data.records
      total.value = res.data.total
    }
  } catch (e) {
    console.error(e)
  } finally {
    previewLoading.value = false
  }
}
</script>

<style scoped lang="scss">
.export-form { padding: 10px 0; max-width: 500px; }
</style>
