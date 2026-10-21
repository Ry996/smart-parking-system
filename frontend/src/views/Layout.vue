<template>
  <el-container class="layout-container">
    <el-aside width="240px" class="sidebar">
      <div class="logo-area">
        <div class="logo-mark">
          <el-icon :size="26"><MapLocation /></el-icon>
        </div>
        <div>
          <div class="logo-title">智慧停车场</div>
          <div class="logo-subtitle">SMART PARKING · V2.1</div>
        </div>
      </div>

      <el-menu
        :default-active="route.path"
        class="side-menu"
        background-color="transparent"
        text-color="#94a3b8"
        active-text-color="#e2f7ff"
      >
        <el-menu-item index="/dashboard" @click="router.push('/dashboard')">
          <el-icon><Odometer /></el-icon><span>首页概览</span>
        </el-menu-item>
        <el-menu-item index="/entry" @click="router.push('/entry')">
          <el-icon><Upload /></el-icon><span>车辆入场</span>
        </el-menu-item>
        <el-menu-item index="/exit" @click="router.push('/exit')">
          <el-icon><Download /></el-icon><span>车辆离场</span>
        </el-menu-item>
        <el-menu-item index="/records" @click="router.push('/records')">
          <el-icon><Notebook /></el-icon><span>停车记录</span>
        </el-menu-item>
        <el-menu-item index="/stats" @click="router.push('/stats')">
          <el-icon><TrendCharts /></el-icon><span>数据统计</span>
        </el-menu-item>
        <el-menu-item
          v-if="userStore.hasPermission('ai:ask')"
          index="/assistant"
          @click="router.push('/assistant')"
        >
          <el-icon><ChatDotRound /></el-icon><span>AI 知识库问答</span>
        </el-menu-item>

        <el-sub-menu v-if="userStore.isAdmin" index="operation">
          <template #title>
            <el-icon><Tickets /></el-icon><span>运营管理</span>
          </template>
          <el-menu-item index="/monthly" @click="router.push('/monthly')">
            <el-icon><Calendar /></el-icon><span>月租管理</span>
          </el-menu-item>
          <el-menu-item index="/reservations" @click="router.push('/reservations')">
            <el-icon><Clock /></el-icon><span>车位预约</span>
          </el-menu-item>
          <el-menu-item index="/blacklist" @click="router.push('/blacklist')">
            <el-icon><CircleCloseFilled /></el-icon><span>黑名单管理</span>
          </el-menu-item>
        </el-sub-menu>

        <el-sub-menu v-if="userStore.isAdmin" index="system">
          <template #title>
            <el-icon><Setting /></el-icon><span>系统管理</span>
          </template>
          <el-menu-item index="/fee-rules" @click="router.push('/fee-rules')">
            <el-icon><PriceTag /></el-icon><span>收费规则</span>
          </el-menu-item>
          <el-menu-item index="/users" @click="router.push('/users')">
            <el-icon><UserFilled /></el-icon><span>用户管理</span>
          </el-menu-item>
          <el-menu-item index="/roles" @click="router.push('/roles')">
            <el-icon><Lock /></el-icon><span>角色权限</span>
          </el-menu-item>
          <el-menu-item index="openapi-docs" @click="openDocs">
            <el-icon><Document /></el-icon><span>接口文档</span>
          </el-menu-item>
          <el-menu-item index="/spaces" @click="router.push('/spaces')">
            <el-icon><Grid /></el-icon><span>车位管理</span>
          </el-menu-item>
          <el-menu-item index="/logs" @click="router.push('/logs')">
            <el-icon><Memo /></el-icon><span>操作日志</span>
          </el-menu-item>
        </el-sub-menu>
      </el-menu>

      <div class="sidebar-foot">
        <div class="foot-line"></div>
        <span>智慧停车运营中心</span>
      </div>
    </el-aside>

    <el-container>
      <el-header class="topbar">
        <div class="topbar-left">
          <div class="page-title">{{ route.meta.title }}</div>
          <div class="page-subtitle">当前为本地真实车牌识别模式</div>
        </div>
        <div class="user-area">
          <el-tag :type="userStore.isAdmin ? 'danger' : 'primary'" effect="dark" size="small">
            {{ userStore.isAdmin ? "管理员" : "操作员" }}
          </el-tag>
          <span class="user-name">{{ userStore.real_name || userStore.username }}</span>
          <el-button text class="logout-btn" @click="logout">
            <el-icon><SwitchButton /></el-icon>
            <span>退出登录</span>
          </el-button>
        </div>
      </el-header>

      <el-main class="content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { useRoute, useRouter } from "vue-router"
import { useUserStore } from "../store/user"

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const logout = () => {
  userStore.logout()
  router.push("/login")
}

// 接口文档由后端 /api/docs 提供，新标签页打开（实验二：接口文档化）
const openDocs = () => window.open("/api/docs", "_blank")
</script>

<style scoped>
.layout-container {
  min-height: 100vh;
  background: var(--bg-app);
}

.sidebar {
  background:
    radial-gradient(400px 300px at 30% -10%, rgba(56, 189, 248, 0.14) 0%, transparent 60%),
    linear-gradient(180deg, #0c1a33 0%, #0f2440 100%);
  border-right: 1px solid rgba(148, 163, 184, 0.14);
  display: flex;
  flex-direction: column;
}

.logo-area {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 22px 20px 18px;
}

.logo-mark {
  width: 44px;
  height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 13px;
  color: #ffffff;
  background: linear-gradient(135deg, #38bdf8 0%, #818cf8 100%);
  box-shadow: 0 0 18px rgba(56, 189, 248, 0.45);
}

.logo-title {
  font-size: 18px;
  font-weight: 800;
  color: #e2e8f0;
  letter-spacing: 1px;
}

.logo-subtitle {
  font-size: 11px;
  color: #64748b;
  letter-spacing: 1px;
  margin-top: 4px;
}

.side-menu {
  flex: 1;
  border-right: none;
  padding: 4px 10px;
}

.side-menu :deep(.el-menu-item),
.side-menu :deep(.el-sub-menu__title) {
  height: 46px;
  line-height: 46px;
  border-radius: 10px;
  margin-bottom: 4px;
}

.side-menu :deep(.el-menu-item:hover),
.side-menu :deep(.el-sub-menu__title:hover) {
  background: rgba(56, 189, 248, 0.1);
  color: #cfefff;
}

.side-menu :deep(.el-menu-item.is-active) {
  background: linear-gradient(90deg, rgba(56, 189, 248, 0.2), rgba(129, 140, 248, 0.1));
  color: #e2f7ff;
  border-left: 3px solid #38bdf8;
  font-weight: 600;
}

.side-menu :deep(.el-sub-menu .el-menu-item) {
  padding-left: 46px !important;
  height: 40px;
  line-height: 40px;
}

.sidebar-foot {
  padding: 14px 20px;
  color: #475569;
  font-size: 12px;
  letter-spacing: 1px;
}

.foot-line {
  height: 1px;
  margin-bottom: 12px;
  background: linear-gradient(90deg, rgba(56, 189, 248, 0.4), transparent);
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 64px;
  background: rgba(13, 27, 46, 0.78);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(148, 163, 184, 0.12);
}

.page-title {
  font-size: 20px;
  font-weight: 700;
  color: #e2e8f0;
}

.page-subtitle {
  margin-top: 3px;
  font-size: 12px;
  color: #64748b;
}

.user-area {
  display: flex;
  align-items: center;
  gap: 14px;
}

.user-name {
  color: #cbd5e1;
  font-weight: 600;
}

.logout-btn {
  color: #94a3b8;
}

.logout-btn:hover {
  color: #f87171;
}

.content {
  background:
    radial-gradient(900px 420px at 85% -10%, rgba(56, 189, 248, 0.05) 0%, transparent 60%),
    radial-gradient(800px 400px at -5% 30%, rgba(129, 140, 248, 0.05) 0%, transparent 55%),
    linear-gradient(180deg, #0b1220 0%, #0d1b2e 100%);
  padding: 24px;
}
</style>
