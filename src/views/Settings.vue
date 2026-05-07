<template>
  <div class="page-settings">
    <el-row :gutter="20">
      <el-col :span="16">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>用户管理</span>
              <el-button type="primary" size="small" @click="showAddDialog">
                <el-icon><Plus /></el-icon> 新增用户
              </el-button>
            </div>
          </template>

          <el-table :data="userList" stripe>
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="username" label="用户名" width="120" />
            <el-table-column prop="real_name" label="姓名" width="120" />
            <el-table-column prop="role" label="角色" width="100">
              <template #default="{ row }">
                <el-tag :type="row.role === 'admin' ? 'danger' : 'info'" size="small">
                  {{ row.role === 'admin' ? '管理员' : '操作员' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">
                  {{ row.status === 1 ? '启用' : '禁用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="last_login" label="最后登录" width="180" />
            <el-table-column label="操作" width="150">
              <template #default="{ row }">
                <el-button type="primary" size="small" text @click="showEditDialog(row)">编辑</el-button>
                <el-button type="danger" size="small" text :disabled="row.id === 1" @click="deleteUser(row.id)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card shadow="hover">
          <template #header><span>系统信息</span></template>
          <div class="sys-info">
            <div class="sys-item">
              <span class="sys-label">系统版本</span>
              <span class="sys-value">v1.0.0</span>
            </div>
            <div class="sys-item">
              <span class="sys-label">前端框架</span>
              <span class="sys-value">Vue 3 + Vite</span>
            </div>
            <div class="sys-item">
              <span class="sys-label">UI 组件库</span>
              <span class="sys-value">Element Plus</span>
            </div>
            <div class="sys-item">
              <span class="sys-label">后端框架</span>
              <span class="sys-value">Flask</span>
            </div>
            <div class="sys-item">
              <span class="sys-label">预测模型</span>
              <span class="sys-value">DLinear</span>
            </div>
          </div>
        </el-card>

        <el-card shadow="hover" style="margin-top: 20px">
          <template #header><span>操作日志</span></template>
          <div class="log-list">
            <div v-for="log in logs" :key="log.id" class="log-item">
              <span class="log-time">{{ log.time }}</span>
              <span class="log-msg">{{ log.message }}</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="userDialogVisible" :title="isEdit ? '编辑用户' : '新增用户'" width="450px">
      <el-form :model="userForm" label-width="70px">
        <el-form-item label="用户名">
          <el-input v-model="userForm.username" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="userForm.real_name" />
        </el-form-item>
        <el-form-item label="密码" v-if="!isEdit">
          <el-input v-model="userForm.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="角色">
          <el-radio-group v-model="userForm.role">
            <el-radio value="admin">管理员</el-radio>
            <el-radio value="operator">操作员</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="userForm.status" :active-value="1" :inactive-value="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="userDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveUser">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { authAPI } from '@/utils/api'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const userList = ref([])
const userDialogVisible = ref(false)
const isEdit = ref(false)
const userForm = reactive({
  id: null,
  username: '',
  real_name: '',
  password: '',
  role: 'operator',
  status: 1
})

const logs = ref([
  { id: 1, time: '14:32:10', message: '用户 admin 登录系统' },
  { id: 2, time: '14:28:05', message: '导出历史数据报表' },
  { id: 3, time: '14:15:33', message: '确认报警 #23' },
  { id: 4, time: '13:45:18', message: '检测到新的严重报警' }
])

async function loadUsers() {
  try {
    const res = await authAPI.getUsers()
    if (res.code === 200) {
      userList.value = res.data
    }
  } catch (e) {
    console.error(e)
  }
}

function showAddDialog() {
  isEdit.value = false
  Object.assign(userForm, { id: null, username: '', real_name: '', password: '', role: 'operator', status: 1 })
  userDialogVisible.value = true
}

function showEditDialog(row) {
  isEdit.value = true
  Object.assign(userForm, { id: row.id, username: row.username, real_name: row.real_name, password: '', role: row.role, status: row.status })
  userDialogVisible.value = true
}

async function handleSaveUser() {
  try {
    const data = { real_name: userForm.real_name, role: userForm.role, status: userForm.status }
    if (!isEdit.value) {
      data.username = userForm.username
      data.password = userForm.password
    }
    const res = isEdit.value
      ? await authAPI.updateUser(userForm.id, data)
      : await authAPI.createUser(data)
    if (res.code === 200) {
      ElMessage.success('保存成功')
      userDialogVisible.value = false
      loadUsers()
    }
  } catch (e) {}
}

async function deleteUser(id) {
  try {
    await ElMessageBox.confirm('确定要删除该用户吗？', '提示', { type: 'warning' })
    const res = await authAPI.deleteUser(id)
    if (res.code === 200) {
      ElMessage.success('删除成功')
      loadUsers()
    }
  } catch (e) {}
}

onMounted(() => {
  loadUsers()
})
</script>

<style scoped lang="scss">
.card-header { display: flex; align-items: center; justify-content: space-between; font-weight: 600; }
.sys-info { padding: 8px 0; }
.sys-item { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #f0f0f0; &:last-child { border-bottom: none; } }
.sys-label { color: #909399; }
.sys-value { color: #303133; font-weight: 500; }
.log-list { max-height: 300px; overflow-y: auto; }
.log-item { padding: 8px 0; border-bottom: 1px dashed #f0f0f0; font-size: 13px; display: flex; gap: 8px; }
.log-time { color: #909399; flex-shrink: 0; }
.log-msg { color: #606266; }
</style>
