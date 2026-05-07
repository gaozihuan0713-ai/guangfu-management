<template>
  <div class="login-container">
    <div class="login-bg">
      <div class="login-particles"></div>
    </div>
    <div class="login-card">
      <div class="login-header">
        <div class="login-icon">
          <el-icon :size="48"><Sunny /></el-icon>
        </div>
        <h1>光伏发电管理平台</h1>
        <p>Photovoltaic Power Management Platform</p>
      </div>
      <el-form ref="formRef" :model="form" :rules="rules" class="login-form" @submit.prevent="handleLogin">
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="请输入用户名"
            size="large"
            :prefix-icon="User"
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            size="large"
            :prefix-icon="Lock"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" class="login-btn" :loading="loading" @click="handleLogin">
            登 录
          </el-button>
        </el-form-item>
      </el-form>
      <div class="login-footer">
        <span>默认账户: admin / admin123</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { User, Lock, Sunny } from '@element-plus/icons-vue'
import { authAPI } from '@/utils/api'

const router = useRouter()
const formRef = ref(null)
const loading = ref(false)

const form = reactive({
  username: '',
  password: ''
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

async function handleLogin() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        const res = await authAPI.login(form.username, form.password)
        if (res.code === 200) {
          localStorage.setItem('solar_token', res.data.token)
          localStorage.setItem('solar_user', JSON.stringify(res.data.user))
          router.push('/')
        }
      } finally {
        loading.value = false
      }
    }
  })
}
</script>

<style scoped lang="scss">
.login-container {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #0c1445 0%, #1a237e 50%, #0d47a1 100%);
  position: relative;
  overflow: hidden;
}

.login-bg {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 20% 80%, rgba(64,158,255,0.15) 0%, transparent 50%),
    radial-gradient(circle at 80% 20%, rgba(103,194,58,0.1) 0%, transparent 50%);
}

.login-particles {
  position: absolute;
  inset: 0;
  background-image:
    radial-gradient(2px 2px at 20% 30%, rgba(255,255,255,0.3), transparent),
    radial-gradient(2px 2px at 40% 70%, rgba(255,255,255,0.2), transparent),
    radial-gradient(1px 1px at 60% 20%, rgba(255,255,255,0.3), transparent),
    radial-gradient(1px 1px at 80% 60%, rgba(255,255,255,0.2), transparent);
  animation: drift 20s ease-in-out infinite;
}

@keyframes drift {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-20px); }
}

.login-card {
  position: relative;
  width: 420px;
  padding: 48px 40px;
  background: rgba(255,255,255,0.08);
  backdrop-filter: blur(20px);
  border-radius: 16px;
  border: 1px solid rgba(255,255,255,0.15);
  box-shadow: 0 20px 60px rgba(0,0,0,0.3);
}

.login-header {
  text-align: center;
  margin-bottom: 36px;
}

.login-icon {
  width: 80px;
  height: 80px;
  margin: 0 auto 16px;
  background: linear-gradient(135deg, #409eff, #67c23a);
  border-radius: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.login-header h1 {
  color: #fff;
  font-size: 24px;
  margin-bottom: 8px;
  font-weight: 600;
}

.login-header p {
  color: rgba(255,255,255,0.5);
  font-size: 13px;
  letter-spacing: 1px;
}

.login-form {
  .el-input__wrapper {
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.15);
    box-shadow: none;
  }
  .el-input__inner {
    color: #fff;
  }
  .el-input__inner::placeholder {
    color: rgba(255,255,255,0.4);
  }
}

.login-btn {
  width: 100%;
  height: 44px;
  font-size: 16px;
  border-radius: 8px;
  background: linear-gradient(135deg, #409eff, #337ecc);
  border: none;
}

.login-footer {
  text-align: center;
  margin-top: 16px;
  color: rgba(255,255,255,0.4);
  font-size: 12px;
}
</style>
