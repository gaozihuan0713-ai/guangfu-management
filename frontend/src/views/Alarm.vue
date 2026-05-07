<template>
  <div class="page-alarm">
    <el-row :gutter="20" class="alarm-cards">
      <el-col :span="6">
        <div class="mini-stat critical-bg">
          <div class="mini-num">{{ alarmStats.by_level?.critical || 0 }}</div>
          <div class="mini-label">严重报警</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="mini-stat warning-bg">
          <div class="mini-num">{{ alarmStats.by_level?.warning || 0 }}</div>
          <div class="mini-label">警告</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="mini-stat today-bg">
          <div class="mini-num">{{ alarmStats.today_count || 0 }}</div>
          <div class="mini-label">今日新增</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="mini-stat unacked-bg">
          <div class="mini-num">{{ alarmStats.by_status?.unacked || 0 }}</div>
          <div class="mini-label">待确认</div>
        </div>
      </el-col>
    </el-row>

    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>报警记录</span>
          <div>
            <el-button type="primary" size="small" :loading="checkLoading" @click="runAlarmCheck">
              <el-icon><Refresh /></el-icon> 检测报警
            </el-button>
            <el-button type="warning" size="small" :disabled="selectedRows.length === 0" @click="batchAck">
              批量确认
            </el-button>
          </div>
        </div>
      </template>

      <div class="filter-bar">
        <el-select v-model="filter.status" placeholder="状态" clearable size="small" style="width: 120px" @change="loadAlarms">
          <el-option label="待确认" value="unacked"></el-option>
          <el-option label="已确认" value="acked"></el-option>
          <el-option label="已解除" value="resolved"></el-option>
        </el-select>
        <el-select v-model="filter.level" placeholder="级别" clearable size="small" style="width: 120px" @change="loadAlarms">
          <el-option label="严重" value="critical"></el-option>
          <el-option label="警告" value="warning"></el-option>
          <el-option label="提示" value="info"></el-option>
        </el-select>
        <el-button type="primary" size="small" @click="loadAlarms">查询</el-button>
        <el-button size="small" @click="resetFilter">重置</el-button>
      </div>

      <el-table :data="alarmList" stripe @selection-change="handleSelection">
        <el-table-column type="selection" width="50" />
        <el-table-column prop="timestamp" label="报警时间" width="180" />
        <el-table-column prop="level" label="级别" width="80">
          <template #default="{ row }">
            <el-tag :type="levelType(row.level)" size="small">{{ levelLabel(row.level) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="alarm_type" label="类型" width="120">
          <template #default="{ row }">
            {{ alarmTypeLabel(row.alarm_type) }}
          </template>
        </el-table-column>
        <el-table-column prop="message" label="报警信息" min-width="280" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button v-if="row.status === 'unacked'" type="warning" size="small" text @click="ackAlarm(row.id)">确认</el-button>
            <el-button v-if="row.status !== 'resolved'" type="success" size="small" text @click="resolveAlarm(row.id)">解除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="page"
          :page-size="20"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="loadAlarms"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { alarmAPI } from '@/utils/api'
import { Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const alarmList = ref([])
const total = ref(0)
const page = ref(1)
const checkLoading = ref(false)
const selectedRows = ref([])
const filter = reactive({ status: '', level: '', alarm_type: '' })
const alarmStats = reactive({ by_level: {}, by_status: {}, today_count: 0 })

function levelType(level) {
  const map = { critical: 'danger', warning: 'warning', info: 'info' }
  return map[level] || 'info'
}
function levelLabel(level) {
  const map = { critical: '严重', warning: '警告', info: '提示' }
  return map[level] || level
}
function statusType(status) {
  const map = { unacked: 'danger', acked: 'warning', resolved: 'success' }
  return map[status] || 'info'
}
function statusLabel(status) {
  const map = { unacked: '待确认', acked: '已确认', resolved: '已解除' }
  return map[status] || status
}
function alarmTypeLabel(type) {
  const map = { zero_output: '高辐射零输出', high_deviation: '功率偏差过大' }
  return map[type] || type
}

async function loadAlarms() {
  try {
    const res = await alarmAPI.getAlarms({ page: page.value, per_page: 20, ...filter })
    if (res.code === 200) {
      alarmList.value = res.data.records
      total.value = res.data.total
    }
  } catch (e) {
    console.error(e)
  }
}

async function loadStats() {
  try {
    const res = await alarmAPI.getStats()
    if (res.code === 200) {
      Object.assign(alarmStats, res.data)
    }
  } catch (e) {
    console.error(e)
  }
}

async function runAlarmCheck() {
  checkLoading.value = true
  try {
    const res = await alarmAPI.checkAlarms()
    if (res.code === 200) {
      ElMessage.success(res.message)
      loadAlarms()
      loadStats()
    }
  } catch (e) {
    console.error(e)
  } finally {
    checkLoading.value = false
  }
}

async function ackAlarm(id) {
  try {
    const res = await alarmAPI.ackAlarm(id)
    if (res.code === 200) {
      ElMessage.success('已确认')
      loadAlarms()
      loadStats()
    }
  } catch (e) {}
}

async function resolveAlarm(id) {
  try {
    const res = await alarmAPI.resolveAlarm(id)
    if (res.code === 200) {
      ElMessage.success('已解除')
      loadAlarms()
      loadStats()
    }
  } catch (e) {}
}

function handleSelection(selection) {
  selectedRows.value = selection.filter(s => s.status === 'unacked').map(s => s.id)
}

async function batchAck() {
  if (selectedRows.value.length === 0) return
  try {
    const res = await alarmAPI.batchAck(selectedRows.value)
    if (res.code === 200) {
      ElMessage.success(res.message)
      loadAlarms()
      loadStats()
    }
  } catch (e) {}
}

function resetFilter() {
  filter.status = ''
  filter.level = ''
  filter.alarm_type = ''
  page.value = 1
  loadAlarms()
}

onMounted(() => {
  loadAlarms()
  loadStats()
})
</script>

<style scoped lang="scss">
.alarm-cards { margin-bottom: 16px; }
.mini-stat { padding: 20px; border-radius: 8px; text-align: center; color: #fff; }
.mini-num { font-size: 28px; font-weight: 700; }
.mini-label { font-size: 13px; opacity: 0.85; margin-top: 4px; }
.critical-bg { background: linear-gradient(135deg, #f56c6c, #dd5a5a); }
.warning-bg { background: linear-gradient(135deg, #e6a23c, #cf8e24); }
.unacked-bg { background: linear-gradient(135deg, #909399, #73767a); }
.today-bg { background: linear-gradient(135deg, #409eff, #337ecc); }
.card-header { display: flex; align-items: center; justify-content: space-between; font-weight: 600; }
.filter-bar { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.pagination-wrap { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>
