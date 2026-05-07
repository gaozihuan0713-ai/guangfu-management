<template>
  <el-container class="main-container">
    <el-aside :width="isCollapse ? '64px' : '220px'" class="sidebar">
      <div class="sidebar-logo">
        <el-icon v-if="isCollapse" :size="28"><Sunny /></el-icon>
        <template v-else>
          <el-icon :size="24"><Sunny /></el-icon>
          <span>光伏管理平台</span>
        </template>
      </div>
      <el-menu
        :default-active="currentRoute"
        :collapse="isCollapse"
        background-color="#1d1e2c"
        text-color="#8a8ea8"
        active-text-color="#409eff"
        @select="handleMenuSelect"
      >
        <el-menu-item index="dashboard">
          <el-icon><DataBoard /></el-icon>
          <template #title>系统首页</template>
        </el-menu-item>
        <el-menu-item index="prediction">
          <el-icon><TrendCharts /></el-icon>
          <template #title>发电预测</template>
        </el-menu-item>
        <el-menu-item index="comparison">
          <el-icon><DataLine /></el-icon>
          <template #title>功率对比</template>
        </el-menu-item>
        <el-menu-item index="report">
          <el-icon><Document /></el-icon>
          <template #title>报表导出</template>
        </el-menu-item>
        <el-menu-item index="alarm">
          <el-icon><AlarmClock /></el-icon>
          <template #title>故障报警</template>
        </el-menu-item>
        <el-menu-item index="history">
          <el-icon><Clock /></el-icon>
          <template #title>历史数据</template>
        </el-menu-item>
        <el-menu-item v-if="currentUser.role === 'admin'" index="settings">
          <el-icon><Setting /></el-icon>
          <template #title>系统设置</template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container class="content-container">
      <el-header class="top-header">
        <div class="header-left">
          <el-icon class="collapse-btn" :size="20" @click="isCollapse = !isCollapse">
            <Fold v-if="!isCollapse" /><Expand v-else />
          </el-icon>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item>{{ menuLabels[currentRoute] }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <el-badge :value="alarmStats.unacked || 0" :hidden="alarmStats.unacked === 0" class="alarm-badge">
            <el-button :icon="Bell" circle size="small" @click="router.push('/alarm')" />
          </el-badge>
          <el-dropdown @command="handleUserCommand">
            <span class="user-dropdown">
              <el-avatar :size="32" class="user-avatar">
                {{ currentUser.real_name ? currentUser.real_name[0] : 'A' }}
              </el-avatar>
              <span class="user-name">{{ currentUser.real_name || currentUser.username }}</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="password">修改密码</el-dropdown-item>
                <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>

  <el-dialog v-model="passwordDialogVisible" title="修改密码" width="400px">
    <el-form :model="passwordForm" label-width="80px">
      <el-form-item label="原密码">
        <el-input v-model="passwordForm.old_password" type="password" show-password />
      </el-form-item>
      <el-form-item label="新密码">
        <el-input v-model="passwordForm.new_password" type="password" show-password />
      </el-form-item>
      <el-form-item label="确认密码">
        <el-input v-model="passwordForm.confirm_password" type="password" show-password />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="passwordDialogVisible = false">取消</el-button>
      <el-button type="primary" @click="handleChangePassword">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { authAPI, alarmAPI } from '@/utils/api'
import {
  Sunny, DataBoard, TrendCharts, DataLine, Document,
  AlarmClock, Clock, Setting, Fold, Expand, Bell, ArrowDown
} from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const isCollapse = ref(false)

const currentUser = reactive(JSON.parse(localStorage.getItem('solar_user') || '{}'))
const alarmStats = reactive({ unacked: 0 })
const passwordDialogVisible = ref(false)
const passwordForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

const currentRoute = computed(() => route.name?.toLowerCase() || 'dashboard')

const menuLabels = {
  dashboard: '系统首页',
  prediction: '发电预测',
  comparison: '功率对比',
  report: '报表导出',
  alarm: '故障报警',
  history: '历史数据',
  settings: '系统设置'
}

function handleMenuSelect(index) {
  router.push({ name: index.charAt(0).toUpperCase() + index.slice(1) })
}

function handleUserCommand(cmd) {
  if (cmd === 'logout') {
    localStorage.removeItem('solar_token')
    localStorage.removeItem('solar_user')
    router.push('/login')
  } else if (cmd === 'password') {
    passwordDialogVisible.value = true
  }
}

async function handleChangePassword() {
  if (passwordForm.new_password !== passwordForm.confirm_password) {
    ElMessage.warning('两次密码不一致')
    return
  }
  if (passwordForm.new_password.length < 6) {
    ElMessage.warning('密码长度不能少于6位')
    return
  }
  try {
    const res = await authAPI.changePassword(passwordForm.old_password, passwordForm.new_password)
    if (res.code === 200) {
      ElMessage.success('密码修改成功')
      passwordDialogVisible.value = false
      Object.assign(passwordForm, { old_password: '', new_password: '', confirm_password: '' })
    }
  } catch (e) {
    // error already handled by interceptor
  }
}

async function loadAlarmStats() {
  try {
    const res = await alarmAPI.getStats()
    if (res.code === 200) {
      alarmStats.unacked = res.data.by_status?.unacked || 0
    }
  } catch (e) {
    console.error('Failed to load alarm stats:', e)
  }
}

onMounted(() => {
  loadAlarmStats()
  setInterval(loadAlarmStats, 30000)
})
</script>

<style scoped lang="scss">
.main-container {
  height: 100vh;
}

.sidebar {
  background: #1d1e2c;
  transition: width 0.3s;
  overflow-x: hidden;
  box-shadow: 2px 0 8px rgba(0,0,0,0.15);
}

.sidebar-logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  border-bottom: 1px solid rgba(255,255,255,0.08);
  white-space: nowrap;
  padding: 0 16px;
}

.sidebar .el-menu {
  border-right: none;
}

.sidebar .el-menu-item {
  margin: 4px 8px;
  border-radius: 8px;
  height: 44px;
}

.sidebar .el-menu-item.is-active {
  background: rgba(64,158,255,0.15) !important;
}

.top-header {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  background: #fff;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
  z-index: 10;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.collapse-btn {
  cursor: pointer;
  color: #606266;
  transition: color 0.2s;
  &:hover { color: #409eff; }
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.user-dropdown {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: #606266;
}

.user-avatar {
  background: linear-gradient(135deg, #409eff, #67c23a);
  color: #fff;
  font-size: 14px;
}

.user-name { font-size: 14px; }
.alarm-badge { margin-right: 8px; }

.main-content {
  background: #f0f2f5;
  padding: 20px;
  overflow-y: auto;
}
</style>
