<template>
  <el-card shadow="hover">
    <template #header>
      <div class="header-title">
        <el-icon><Memo /></el-icon>
        <span>操作日志（审计）</span>
      </div>
    </template>

    <el-form inline>
      <el-form-item label="操作人">
        <el-input v-model="filters.username" placeholder="用户名" clearable style="width: 150px" @keyup.enter="search" />
      </el-form-item>
      <el-form-item label="操作类型">
        <el-select v-model="filters.action" clearable style="width: 150px" @change="search">
          <el-option label="登录成功" value="login" />
          <el-option label="登录失败" value="login_fail" />
          <el-option label="车辆入场" value="enter" />
          <el-option label="车辆离场" value="exit" />
          <el-option label="拦截记录" value="block" />
          <el-option label="新增" value="create" />
          <el-option label="修改" value="update" />
          <el-option label="删除" value="delete" />
          <el-option label="导出" value="export" />
        </el-select>
      </el-form-item>
      <el-form-item label="日期范围">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          value-format="YYYY-MM-DD"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
        />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="search">查询</el-button>
        <el-button @click="reset">重置</el-button>
      </el-form-item>
    </el-form>

    <el-table :data="logs" stripe v-loading="loading">
      <el-table-column prop="created_at" label="操作时间" width="170" />
      <el-table-column prop="username" label="操作人" width="120" />
      <el-table-column prop="action" label="操作类型" width="110">
        <template #default="{ row }">
          <el-tag :type="actionTag(row.action)" size="small">{{ actionText(row.action) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="target" label="操作对象" min-width="140" />
      <el-table-column prop="detail" label="操作详情" min-width="220" show-overflow-tooltip />
      <el-table-column prop="ip" label="IP 地址" width="130" />
    </el-table>

    <el-pagination
      v-model:current-page="page"
      :page-size="perPage"
      :total="total"
      layout="total, prev, pager, next"
      class="pager"
      @current-change="loadLogs"
    />
  </el-card>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { getLogs } from '../api'

const logs = ref([])
const loading = ref(false)
const filters = ref({ username: '', action: '' })
const dateRange = ref([])
const page = ref(1)
const perPage = ref(15)
const total = ref(0)

const actionTextMap = {
  login: '登录成功',
  login_fail: '登录失败',
  enter: '车辆入场',
  exit: '车辆离场',
  block: '拦截记录',
  create: '新增',
  update: '修改',
  delete: '删除',
  export: '导出',
}
const actionTagMap = {
  login: 'success',
  login_fail: 'danger',
  enter: 'primary',
  exit: 'primary',
  block: 'warning',
  create: 'success',
  update: 'primary',
  delete: 'danger',
  export: 'info',
}
const actionText = (a) => actionTextMap[a] || a
const actionTag = (a) => actionTagMap[a] || 'info'

const loadLogs = async () => {
  loading.value = true
  try {
    const res = await getLogs({
      page: page.value,
      per_page: perPage.value,
      username: filters.value.username,
      action: filters.value.action,
      date_from: dateRange.value?.[0] || '',
      date_to: dateRange.value?.[1] || '',
    })
    if (res.code === 200) {
      logs.value = res.data.items || []
      total.value = res.data.total || 0
    }
  } finally {
    loading.value = false
  }
}

const search = () => {
  page.value = 1
  loadLogs()
}

const reset = () => {
  filters.value = { username: '', action: '' }
  dateRange.value = []
  page.value = 1
  loadLogs()
}

onMounted(loadLogs)
</script>

<style scoped>
.pager {
  margin-top: 16px;
  justify-content: flex-end;
}
</style>
