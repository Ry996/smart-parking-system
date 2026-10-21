import { createRouter, createWebHistory } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../store/user'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { noAuth: true, title: '登录' },
  },
  {
    path: '/',
    component: () => import('../views/Layout.vue'),
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', name: 'Dashboard', component: () => import('../views/Dashboard.vue'), meta: { title: '首页概览' } },
      { path: 'entry', name: 'Entry', component: () => import('../views/Entry.vue'), meta: { title: '车辆入场' } },
      { path: 'exit', name: 'Exit', component: () => import('../views/Exit.vue'), meta: { title: '车辆离场' } },
      { path: 'records', name: 'Records', component: () => import('../views/Records.vue'), meta: { title: '停车记录' } },
      { path: 'stats', name: 'Stats', component: () => import('../views/Stats.vue'), meta: { title: '数据统计' } },
      {
        path: 'assistant',
        name: 'Assistant',
        component: () => import('../views/AiAssistant.vue'),
        meta: { title: 'AI 知识库问答', permission: 'ai:ask' },
      },
      { path: 'fee-rules', name: 'FeeRules', component: () => import('../views/FeeRules.vue'), meta: { title: '收费规则', role: 'admin', permission: 'fee:manage' } },
      { path: 'users', name: 'Users', component: () => import('../views/Users.vue'), meta: { title: '用户管理', role: 'admin', permission: 'user:manage' } },
      { path: 'roles', name: 'Roles', component: () => import('../views/Roles.vue'), meta: { title: '角色权限', role: 'admin', permission: 'role:manage' } },
      { path: 'spaces', name: 'Spaces', component: () => import('../views/Spaces.vue'), meta: { title: '车位管理', role: 'admin', permission: 'space:manage' } },
      { path: 'monthly', name: 'Monthly', component: () => import('../views/Monthly.vue'), meta: { title: '月租管理', role: 'admin', permission: 'monthly:manage' } },
      { path: 'reservations', name: 'Reservations', component: () => import('../views/Reservations.vue'), meta: { title: '车位预约', role: 'admin', permission: 'reservation:manage' } },
      { path: 'blacklist', name: 'Blacklist', component: () => import('../views/Blacklist.vue'), meta: { title: '黑名单管理', role: 'admin', permission: 'blacklist:manage' } },
      { path: 'logs', name: 'Logs', component: () => import('../views/Logs.vue'), meta: { title: '操作日志', role: 'admin', permission: 'log:read' } },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫：先确保已登录，再按后端下发的权限码放行。
// 注意这只是体验层控制，真正的鉴权在后端 permission_required 装饰器里。
router.beforeEach(async (to, from, next) => {
  const userStore = useUserStore()
  document.title = `${to.meta.title || '智能停车场'} - 智能停车场管理系统`

  if (to.meta.noAuth) {
    next()
    return
  }

  if (!userStore.isLogin) {
    next('/login')
    return
  }

  if (!userStore.permissionsLoaded) {
    try {
      const { getMyPermissions } = await import('../api')
      const res = await getMyPermissions()
      if (res.code === 200) {
        userStore.setPermissions(res.data.permissions)
      }
    } catch (error) {
      // 权限加载失败时按最小权限处理，不阻塞页面
      userStore.setPermissions([])
    }
  }

  if (to.meta.permission && !userStore.hasPermission(to.meta.permission)) {
    ElMessage.warning('当前账号没有该功能权限。')
    next('/dashboard')
    return
  }

  if (to.meta.role === 'admin' && !userStore.isAdmin) {
    next('/dashboard')
    return
  }

  next()
})

export default router
