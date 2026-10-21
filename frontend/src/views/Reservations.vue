<template>
  <el-card shadow="hover">
    <template #header>
      <div class="header-row">
        <div class="header-title">
          <el-icon><Clock /></el-icon>
          <span>车位预约管理</span>
        </div>
        <el-button type="primary" @click="openDialog()">新增预约</el-button>
      </div>
    </template>

    <el-form inline>
      <el-form-item label="关键字">
        <el-input v-model="filters.keyword" placeholder="车牌/预约人" clearable style="width: 200px" @keyup.enter="loadList" />
      </el-form-item>
      <el-form-item label="状态">
        <el-select v-model="filters.status" clearable style="width: 140px" @change="loadList">
          <el-option label="待入场" value="pending" />
          <el-option label="已到达" value="arrived" />
          <el-option label="已取消" value="cancelled" />
          <el-option label="已过期" value="expired" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="loadList">查询</el-button>
      </el-form-item>
    </el-form>

    <el-table :data="list" stripe v-loading="loading">
      <el-table-column prop="plate_number" label="车牌号" width="120" />
      <el-table-column prop="owner_name" label="预约人" width="110" />
      <el-table-column prop="phone" label="联系电话" width="140" />
      <el-table-column prop="start_time" label="预约开始" width="170" />
      <el-table-column prop="end_time" label="预约结束" width="170" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusTag(row.status)">{{ statusText(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="remark" label="备注" show-overflow-tooltip />
      <el-table-column label="操作" width="190" fixed="right">
        <template #default="{ row }">
          <el-button v-if="row.status === 'pending'" text type="success" @click="handleStatus(row, 'arrived')">标记到达</el-button>
          <el-button v-if="row.status === 'pending'" text type="warning" @click="handleStatus(row, 'cancelled')">取消</el-button>
          <el-button text type="danger" @click="handleDelete(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <el-dialog v-model="dialogVisible" title="新增车位预约" width="520px">
    <el-form :model="form" label-width="110px">
      <el-form-item label="车牌号">
        <el-input v-model="form.plate_number" placeholder="如 皖C12345" />
      </el-form-item>
      <el-form-item label="预约人">
        <el-input v-model="form.owner_name" />
      </el-form-item>
      <el-form-item label="联系电话">
        <el-input v-model="form.phone" />
      </el-form-item>
      <el-form-item label="预约时段">
        <el-date-picker
          v-model="form.timeRange"
          type="datetimerange"
          value-format="YYYY-MM-DD HH:mm:ss"
          range-separator="至"
          start-placeholder="开始时间"
          end-placeholder="结束时间"
          style="width: 100%"
        />
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="form.remark" type="textarea" :rows="2" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createReservation, deleteReservation, getReservations, updateReservationStatus } from '../api'

const list = ref([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const filters = ref({ keyword: '', status: '' })
const form = ref({
  plate_number: '',
  owner_name: '',
  phone: '',
  timeRange: [],
  remark: '',
})

const statusText = (s) => ({ pending: '待入场', arrived: '已到达', cancelled: '已取消', expired: '已过期' }[s] || s)
const statusTag = (s) => ({ pending: 'primary', arrived: 'success', cancelled: 'info', expired: 'danger' }[s] || 'info')

const loadList = async () => {
  loading.value = true
  try {
    const res = await getReservations(filters.value)
    if (res.code === 200) {
      list.value = res.data || []
    }
  } finally {
    loading.value = false
  }
}

const openDialog = () => {
  form.value = {
    plate_number: '',
    owner_name: '',
    phone: '',
    timeRange: [],
    remark: '',
  }
  dialogVisible.value = true
}

const handleSave = async () => {
  if (!form.value.plate_number.trim()) {
    ElMessage.warning('请输入车牌号')
    return
  }
  if (!form.value.timeRange || form.value.timeRange.length !== 2) {
    ElMessage.warning('请选择预约时段')
    return
  }

  saving.value = true
  try {
    const res = await createReservation({
      plate_number: form.value.plate_number,
      owner_name: form.value.owner_name,
      phone: form.value.phone,
      start_time: form.value.timeRange[0],
      end_time: form.value.timeRange[1],
      remark: form.value.remark,
    })
    if (res.code === 200) {
      ElMessage.success('预约创建成功')
      dialogVisible.value = false
      await loadList()
    }
  } finally {
    saving.value = false
  }
}

const handleStatus = async (row, status) => {
  const res = await updateReservationStatus(row.id, { status })
  if (res.code === 200) {
    ElMessage.success(status === 'arrived' ? '已标记到达' : '已取消')
    loadList()
  }
}

const handleDelete = async (id) => {
  await ElMessageBox.confirm('确定删除该预约记录吗？', '提示', { type: 'warning' })
  const res = await deleteReservation(id)
  if (res.code === 200) {
    ElMessage.success('删除成功')
    loadList()
  }
}

onMounted(loadList)
</script>

<style scoped>
.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>
