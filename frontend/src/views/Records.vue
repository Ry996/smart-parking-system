<template>
  <el-card shadow="hover">
    <template #header>
      <div class="card-head">
        <el-icon><Notebook /></el-icon>
        <span>停车记录查询</span>
      </div>
    </template>

    <el-form inline>
      <el-form-item label="车牌号">
        <el-input v-model="filters.plate" placeholder="支持模糊查询" clearable />
      </el-form-item>
      <el-form-item label="状态">
        <el-select v-model="filters.status" clearable style="width: 140px">
          <el-option label="在场" value="parked" />
          <el-option label="已离场" value="exited" />
          <el-option label="异常" value="exception" />
        </el-select>
      </el-form-item>
      <el-form-item label="入场日期">
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
        <el-button :loading="exporting" @click="handleExport">导出 CSV</el-button>
      </el-form-item>
    </el-form>

    <el-table :data="records" stripe v-loading="loading">
      <el-table-column prop="plate_number" label="车牌号" width="150" />
      <el-table-column prop="plate_type" label="车牌类型" width="120">
        <template #default="{ row }">{{ plateTypeMap[row.plate_type] || row.plate_type }}</template>
      </el-table-column>
      <el-table-column prop="entry_time" label="入场时间" width="180" />
      <el-table-column prop="exit_time" label="离场时间" width="180" />
      <el-table-column prop="duration" label="停车时长" width="120">
        <template #default="{ row }">{{ row.duration ? `${row.duration} 分钟` : '-' }}</template>
      </el-table-column>
      <el-table-column prop="fee" label="收费金额" width="120">
        <template #default="{ row }">{{ row.fee !== null && row.fee !== undefined ? `¥${row.fee}` : '-' }}</template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="110">
        <template #default="{ row }">{{ statusTextMap[row.status] || row.status }}</template>
      </el-table-column>
      <el-table-column prop="payment_status" label="支付状态" width="110">
        <template #default="{ row }">
          <el-tag :type="paymentTag(row.payment_status)" size="small">{{ paymentText(row.payment_status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="remark" label="备注" show-overflow-tooltip />
      <el-table-column label="操作" width="110" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="row.payment_status === 'unpaid'"
            text
            type="success"
            :loading="payingId === row.id"
            @click="handlePay(row)"
          >补收</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-model:current-page="page"
      :page-size="perPage"
      :total="total"
      layout="total, prev, pager, next"
      class="pager"
      @current-change="loadRecords"
    />
  </el-card>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { exportRecords, getRecords, payRecord } from '../api'

const filters = ref({
  plate: '',
  status: '',
})
const dateRange = ref([])
const records = ref([])
const loading = ref(false)
const exporting = ref(false)
const payingId = ref(null)
const page = ref(1)
const perPage = ref(15)
const total = ref(0)

const plateTypeMap = {
  blue: '蓝牌',
  yellow: '黄牌',
  green: '新能源',
}
const statusTextMap = {
  parked: '在场',
  exited: '已离场',
  exception: '异常',
}

const paymentText = (s) => ({ unpaid: '待支付', paid: '已支付', free: '免费' }[s] || s)
const paymentTag = (s) => ({ unpaid: 'warning', paid: 'success', free: 'info' }[s] || 'info')

const handlePay = async (row) => {
  payingId.value = row.id
  try {
    const res = await payRecord(row.id)
    if (res.code === 200) {
      ElMessage.success(`补收成功：¥${row.fee}`)
      loadRecords()
    }
  } finally {
    payingId.value = null
  }
}

const loadRecords = async () => {
  loading.value = true
  try {
    const res = await getRecords({
      page: page.value,
      per_page: perPage.value,
      plate: filters.value.plate,
      status: filters.value.status,
      date_from: dateRange.value?.[0] || '',
      date_to: dateRange.value?.[1] || '',
    })
    if (res.code === 200) {
      records.value = res.data.items || []
      total.value = res.data.total || 0
    }
  } finally {
    loading.value = false
  }
}

const search = () => {
  page.value = 1
  loadRecords()
}

const reset = () => {
  filters.value = { plate: '', status: '' }
  dateRange.value = []
  page.value = 1
  loadRecords()
}

const handleExport = async () => {
  exporting.value = true
  try {
    const res = await exportRecords({
      plate: filters.value.plate,
      status: filters.value.status,
      date_from: dateRange.value?.[0] || '',
      date_to: dateRange.value?.[1] || '',
    })
    const blob = new Blob([res], { type: 'text/csv' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `停车记录导出_${new Date().toISOString().slice(0, 10)}.csv`
    link.click()
    URL.revokeObjectURL(link.href)
    ElMessage.success('导出成功')
  } finally {
    exporting.value = false
  }
}

onMounted(loadRecords)
</script>

<style scoped>
.card-head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pager {
  margin-top: 16px;
  justify-content: flex-end;
}
</style>
