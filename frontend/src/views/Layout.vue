<template>
  <el-container class="main-container">
    <el-aside :width="isCollapse ? '64px' : '220px'" class="sidebar">
      <div class="sidebar-logo">
        <el-icon :size="28" v-if="isCollapse"><Sunny /></el-icon>
        <template v-else>
          <el-icon :size="24"><Sunny /></el-icon>
          <span>光伏管理平台</span>
        </template>
      </div>
      <el-menu :default-active="currentRoute" :collapse="isCollapse"
        background-color="#1d1e2c" text-color="#8a8ea8" active-text-color="#409eff"
        router>
        <el-menu-item index="/dashboard">
          <el-icon><DataBoard /></el-icon>
          <template #title>系统首页</template>
        </el-menu-item>
        <el-menu-item index="/prediction">
          <el-icon><TrendCharts /></el-icon>
          <template #title>发电预测</template>
        </el-menu-item>
        <el-menu-item index="/comparison">
          <el-icon><DataLine /></el-icon>
          <template #title>功率对比</template>
        </el-menu-item>
        <el-menu-item index="/report">
          <el-icon><Document /></el-icon>
          <template #title>报表导出</template>
        </el-menu-item>
        <el-menu-item index="/alarm">
          <el-icon><AlarmClock /></el-icon>
          <template #title>故障报警</template>
        </el-menu-item>
        <el-menu-item index="/history">
          <el-icon><Clock /></el-icon>
          <template #title>历史数据</template>
        </el-menu-item>
        <el-menu-item index="/settings" v-if="currentUser.role === 'admin'">
          <el-icon><Setting /></el-icon>
          <template #title>系统设置</template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container class="content-container">
      <el-header class="top-header">
        <div class="header-left">
          <el-icon class="collapse-btn" @click="isCollapse = !isCollapse" :size="20">
            <Fold v-if="!isCollapse" /><Expand v-else />
          </el-icon>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item>{{ menuLabels[currentRoute] }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <el-badge :value="alarmStats.unacked || 0" :hidden="!alarmStats.unacked" class="alarm-badge">
            <el-button :icon="Bell" circle size="small" @click="$router.push('/alarm')" />
          </el-badge>
          <el-dropdown @command="handleCommand">
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

    <el-dialog v-model="pwdDialogVisible" title="修改密码" width="400px">
      <el-form :model="pwdForm" label-width="80px">
        <el-form-item label="原密码">
          <el-input v-model="pwdForm.old_password" type="password" />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="pwdForm.new_password" type="password" />
        </el-form-item>
        <el-form-item label="确认密码">
          <el-input v-model="pwdForm.confirm_password" type="password" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pwdDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="changePassword">确定</el-button>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Bell } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import api from '../utils/api'

const router = useRouter()
const route = useRoute()
const isCollapse = ref(false)
const pwdDialogVisible = ref(false)
const pwdForm = reactive({ old_password: '', new_password: '', confirm_password: '' })
const alarmStats = reactive({ unacked: 0 })

const currentUser = reactive(
  JSON.parse(localStorage.getItem('solar_user') || '{}')
)

const currentRoute = computed(() => route.path)
const menuLabels = {
  '/dashboard': '系统首页', '/prediction': '发电预测', '/comparison': '功率对比',
  '/report': '报表导出', '/alarm': '故障报警', '/history': '历史数据', '/settings': '系统设置'
}

async function loadAlarmStats() {
  try {
    const res = await api.getAlarmStats()
    if (res.code === 200) Object.assign(alarmStats, res.data)
  } catch (e) { /* ignore */ }
}

function handleCommand(cmd) {
  if (cmd === 'logout') {
    localStorage.removeItem('solar_token')
    localStorage.removeItem('solar_user')
    router.push('/login')
  } else if (cmd === 'password') {
    pwdDialogVisible.value = true
  }
}

async function changePassword() {
  if (pwdForm.new_password !== pwdForm.confirm_password) {
    return ElMessage.warning('两次密码不一致')
  }
  if (pwdForm.new_password.length < 6) {
    return ElMessage.warning('密码长度不能少于6位')
  }
  const res = await api.changePassword(pwdForm.old_password, pwdForm.new_password)
  if (res.code === 200) {
    ElMessage.success('密码修改成功')
    pwdDialogVisible.value = false
    Object.assign(pwdForm, { old_password: '', new_password: '', confirm_password: '' })
  } else {
    ElMessage.error(res.message)
  }
}

onMounted(() => { loadAlarmStats() })
</script>
