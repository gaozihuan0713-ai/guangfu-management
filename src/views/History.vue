<template>
  <div class="page-history">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>历史数据查询</span>
          <el-button type="primary" size="small" @click="loadHistory">查询</el-button>
        </div>
      </template>

      <div class="filter-bar">
        <el-date-picker v-model="filter.start_date" type="date" placeholder="开始日期" value-format="YYYY-MM-DD" size="small" />
        <el-date-picker v-model="filter.end_date" type="date" placeholder="结束日期" value-format="YYYY-MM-DD" size="small" />
        <el-button size="small" @click="resetFilter">重置</el-button>
      </div>

      <el-table :data="historyList" stripe max-height="500">
        <el-table-column prop="timestamp" label="时间" width="180" />
        <el-table-column prop="active_power" label="有功功率(kW)" width="130" />
        <el-table-column prop="radiation" label="辐照度(W/m²)" width="140" />
        <el-table-column prop="temperature" label="温度(°C)" width="110" />
        <el-table-column prop="humidity" label="湿度(%)" width="100" />
        <el-table-column prop="wind_speed" label="风速(m/s)" width="110" />
        <el-table-column prop="wind_direction" label="风向(°)" width="100" />
        <el-table-column prop="rainfall" label="降雨量(mm)" width="120" />
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="page"
          :page-size="50"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="loadHistory"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { dataAPI } from '@/utils/api'

const historyList = ref([])
const total = ref(0)
const page = ref(1)
const filter = reactive({ start_date: '', end_date: '' })

async function loadHistory() {
  try {
    const res = await dataAPI.getHistory({ page: page.value, per_page: 50, ...filter })
    if (res.code === 200) {
      historyList.value = res.data.records
      total.value = res.data.total
    }
  } catch (e) {
    console.error(e)
  }
}

function resetFilter() {
  filter.start_date = ''
  filter.end_date = ''
  page.value = 1
  loadHistory()
}

onMounted(() => {
  loadHistory()
})
</script>

<style scoped lang="scss">
.card-header { display: flex; align-items: center; justify-content: space-between; font-weight: 600; }
.filter-bar { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.pagination-wrap { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>
