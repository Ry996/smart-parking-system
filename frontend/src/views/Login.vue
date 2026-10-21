<template>
  <div class="login-page">
    <!-- 实景背景 + 蒙版 -->
    <div class="bg-image"></div>
    <div class="bg-overlay"></div>

    <!-- 背景光斑 -->
    <div class="glow glow-a"></div>
    <div class="glow glow-b"></div>
    <div class="glow glow-c"></div>
    <div class="glow glow-d"></div>

    <!-- 流动光束 -->
    <div class="beam beam-1"></div>
    <div class="beam beam-2"></div>

    <!-- 漂浮光点 -->
    <span class="dot" style="left: 10%; top: 78%; width: 6px; height: 6px; --d: 0s; --o: 0.9;"></span>
    <span class="dot" style="left: 18%; top: 58%; width: 4px; height: 4px; --d: 1.2s; --o: 0.6;"></span>
    <span class="dot" style="left: 28%; top: 84%; width: 5px; height: 5px; --d: 2.4s; --o: 0.8;"></span>
    <span class="dot" style="left: 40%; top: 68%; width: 3px; height: 3px; --d: 0.6s; --o: 0.7;"></span>
    <span class="dot" style="left: 60%; top: 82%; width: 6px; height: 6px; --d: 1.8s; --o: 0.9;"></span>
    <span class="dot" style="left: 68%; top: 60%; width: 4px; height: 4px; --d: 3s; --o: 0.6;"></span>
    <span class="dot" style="left: 76%; top: 80%; width: 5px; height: 5px; --d: 0.9s; --o: 0.85;"></span>
    <span class="dot" style="left: 86%; top: 70%; width: 3px; height: 3px; --d: 2s; --o: 0.7;"></span>
    <span class="dot" style="left: 92%; top: 86%; width: 6px; height: 6px; --d: 1.4s; --o: 0.9;"></span>
    <span class="dot" style="left: 6%; top: 38%; width: 4px; height: 4px; --d: 2.8s; --o: 0.6;"></span>

    <div class="login-card">
      <div class="card-top-glow"></div>
      <div class="login-logo">
        <el-icon :size="30"><MapLocation /></el-icon>
      </div>
      <div class="login-header">
        <h2>智慧停车场管理系统</h2>
        <p>车牌识别 · 智能计费 · 运营管理一体化平台</p>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" @submit.prevent="handleLogin">
        <el-form-item prop="username">
          <el-input v-model="form.username" size="large" placeholder="请输入用户名" :prefix-icon="User" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            size="large"
            placeholder="请输入密码"
            :prefix-icon="Lock"
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        <el-form-item>
          <el-button class="login-btn" size="large" :loading="loading" @click="handleLogin">
            {{ loading ? "登录中…" : "登 录 系 统" }}
          </el-button>
        </el-form-item>
      </el-form>

      <div class="login-tips">
        <p>管理员账号：admin / admin123</p>
        <p>操作员账号：operator1 / admin123</p>
      </div>

      <div class="login-foot">V2.1 · 智慧停车运营中心</div>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue"
import { useRouter } from "vue-router"
import { ElMessage } from "element-plus"
import { Lock, User } from "@element-plus/icons-vue"
import { login } from "../api"
import { useUserStore } from "../store/user"

const router = useRouter()
const userStore = useUserStore()
const formRef = ref()
const loading = ref(false)
const form = ref({
  username: "admin",
  password: "admin123",
})

const rules = {
  username: [{ required: true, message: "请输入用户名", trigger: "blur" }],
  password: [{ required: true, message: "请输入密码", trigger: "blur" }],
}

const handleLogin = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    const res = await login(form.value)
    if (res.code === 200) {
      userStore.setUser(res.data)
      ElMessage.success("登录成功")
      router.push("/dashboard")
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  background: #0b1220;
}

/* 实景背景 */
.bg-image {
  position: absolute;
  inset: 0;
  background: url("/login-bg.jpg") center / cover no-repeat;
  filter: saturate(0.82);
}

.bg-overlay {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(180deg, rgba(8, 16, 30, 0.35) 0%, rgba(8, 16, 30, 0.55) 50%, rgba(8, 16, 30, 0.78) 100%),
    radial-gradient(900px 500px at 50% 40%, transparent 0%, rgba(8, 16, 30, 0.5) 100%);
}

/* 光斑 */
.glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(90px);
  pointer-events: none;
  animation: glowDrift 15s ease-in-out infinite alternate;
  z-index: 1;
}

.glow-a {
  width: 460px;
  height: 460px;
  top: -130px;
  right: -110px;
  opacity: 0.42;
  background: radial-gradient(circle, rgba(56, 189, 248, 0.6), transparent 70%);
  animation-delay: 0s;
}

.glow-b {
  width: 520px;
  height: 520px;
  bottom: -190px;
  left: -140px;
  opacity: 0.4;
  background: radial-gradient(circle, rgba(129, 140, 248, 0.55), transparent 70%);
  animation-delay: -5s;
}

.glow-c {
  width: 340px;
  height: 340px;
  top: 34%;
  left: 6%;
  opacity: 0.3;
  background: radial-gradient(circle, rgba(14, 165, 233, 0.5), transparent 70%);
  animation-delay: -9s;
}

.glow-d {
  width: 380px;
  height: 380px;
  bottom: 8%;
  right: 6%;
  opacity: 0.28;
  background: radial-gradient(circle, rgba(192, 132, 252, 0.5), transparent 70%);
  animation-delay: -12s;
}

@keyframes glowDrift {
  0% { transform: translate(0, 0) scale(1); }
  100% { transform: translate(46px, -34px) scale(1.14); }
}

/* 流动光束 */
.beam {
  position: absolute;
  left: -8%;
  right: -8%;
  height: 2px;
  pointer-events: none;
  background: linear-gradient(90deg, transparent 0%, rgba(56, 189, 248, 0.85) 50%, transparent 100%);
  filter: blur(1px);
  animation: beamMove 11s linear infinite;
  z-index: 1;
}

.beam-1 { animation-delay: 0s; }
.beam-2 { animation-delay: 5.5s; }

@keyframes beamMove {
  0% { top: -5%; opacity: 0; }
  8% { opacity: 1; }
  50% { opacity: 0.75; }
  92% { opacity: 1; }
  100% { top: 105%; opacity: 0; }
}

/* 漂浮光点 */
.dot {
  position: absolute;
  border-radius: 50%;
  background: #7dd3fc;
  box-shadow: 0 0 10px rgba(56, 189, 248, 0.9);
  pointer-events: none;
  animation: dotFloat 9s ease-in-out infinite;
  animation-delay: var(--d, 0s);
  z-index: 1;
}

@keyframes dotFloat {
  0%, 100% {
    transform: translateY(0) scale(1);
    opacity: calc(var(--o, 0.8) * 0.35);
  }
  20% { opacity: var(--o, 0.8); }
  50% { transform: translateY(-46px) scale(1.22); opacity: var(--o, 0.8); }
  80% { transform: translateY(10px) scale(0.9); opacity: calc(var(--o, 0.8) * 0.5); }
}

/* 登录卡片 */
.login-card {
  position: relative;
  z-index: 3;
  width: 420px;
  padding: 38px 36px 24px;
  border-radius: 20px;
  background: rgba(10, 22, 42, 0.66);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(56, 189, 248, 0.28);
  box-shadow:
    0 24px 80px rgba(2, 8, 20, 0.65),
    0 0 40px rgba(56, 189, 248, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.07);
  overflow: hidden;
}

/* 卡片顶部光条 */
.card-top-glow {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, #38bdf8, #818cf8, #38bdf8, transparent);
  animation: topShine 4s linear infinite;
  background-size: 220% 100%;
}

@keyframes topShine {
  0% { background-position: 120% 0; }
  100% { background-position: -120% 0; }
}

.login-logo {
  width: 64px;
  height: 64px;
  margin: 0 auto 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 18px;
  color: #ffffff;
  background: linear-gradient(135deg, #38bdf8 0%, #818cf8 100%);
  box-shadow: 0 0 26px rgba(56, 189, 248, 0.55);
}

.login-header {
  text-align: center;
  margin-bottom: 26px;
}

.login-header h2 {
  margin: 0 0 8px;
  font-size: 24px;
  font-weight: 800;
  letter-spacing: 1px;
  background: linear-gradient(90deg, #7dd3fc, #c4b5fd);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.login-header p {
  margin: 0;
  color: #94a3b8;
  font-size: 13px;
}

.login-btn {
  width: 100%;
  font-weight: 700;
  letter-spacing: 2px;
  background: linear-gradient(90deg, #38bdf8 0%, #6366f1 100%);
  border: none;
  color: #fff;
}

.login-btn:hover {
  background: linear-gradient(90deg, #7dd3fc 0%, #818cf8 100%);
}

.login-tips {
  margin-top: 14px;
  padding: 10px 14px;
  border-radius: 10px;
  background: rgba(56, 189, 248, 0.08);
  border: 1px dashed rgba(56, 189, 248, 0.25);
  color: #94a3b8;
  font-size: 12px;
  line-height: 1.9;
}

.login-foot {
  margin-top: 16px;
  text-align: center;
  color: #475569;
  font-size: 12px;
  letter-spacing: 1px;
}
</style>
