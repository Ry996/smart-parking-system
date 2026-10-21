<template>
  <el-card shadow="hover">
    <template #header>
      <div class="header-row">
        <div class="header-title">
          <el-icon><CircleCloseFilled /></el-icon>
          <span>黑名单管理</span>
        </div>
        <el-button type="primary" @click="openDialog()">加入黑名单</el-button>
      </div>
    </template>

    <el-form inline>
      <el-form-item label="车牌号">
        <el-input v-model="filters.keyword" placeholder="支持模糊查询" clearable style="width: 200px" @keyup.enter="loadList" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="loadList">查询</el-button>
      </el-form-item>
    </el-form>

    <el-alert type="warning" show-icon :closable="false" class="tip-alert"
      title="黑名单车辆在入场时会被系统自动拦截，请谨慎操作；解除黑名单后车辆可正常入场。" />

    <el-table :data="list" stripe v-loading="loading">
      <el-table-column prop="plate_number" label="车牌号" width="140" />
      <el-table-column prop="reason" label="拉黑原因" min-width="180" />
      <el-table-column prop="debt_amount" label="欠费金额" width="120">
        <template #default="{ row }">¥{{ row.debt_amount }}</template>
      </el-table-column>
      <el-table-column prop="is_active" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'danger' : 'info'">{{ row.is_active ? '拦截中' : '已解除' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="加入时间" width="170" />
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button text type="primary" @click="openDialog(row)">编辑</el-button>
          <el-button v-if="row.is_active" text type="success" @click="handleToggle(row, 0)">解除</el-button>
          <el-button v-else text type="warning" @click="handleToggle(row, 1)">启用拦截</el-button>
          <el-button text type="danger" @click="handleDelete(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <el-dialog v-model="dialogVisible" :title="editingId ? '编辑黑名单' : '加入黑名单'" width="500px">
    <el-form :model="form" label-width="110px">
      <el-form-item label="车牌号">
        <el-input v-model="form.plate_number" placeholder="如 皖A99999" />
      </el-form-item>
      <el-form-item label="拉黑原因">
        <el-input v-model="form.reason" placeholder="如 恶意逃费 / 长期占位" />
      </el-form-item>
      <el-form-item label="欠费金额">
        <el-input-number v-model="form.debt_amount" :min="0" :step="10" :precision="2" />
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
import { createBlacklist, deleteBlacklist, getBlacklist, updateBlacklist } from '../api'

const list = ref([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editingId = ref(null)
const filters = ref({ keyword: '' })
const form = ref({ plate_number: '', reason: '', debt_amount: 0 })

const loadList = async () => {
  loading.value = true
  try {
    const res = await getBlacklist(filters.value)
    if (res.code === 200) {
      list.value = res.data || []
    }
  } finally {
    loading.value = false
  }
}

const openDialog = (row = null) => {
  editingId.value = row?.id || null
  form.value = row ? { plate_number: row.plate_number, reason: row.reason, debt_amount: row.debt_amount } : { plate_number: '', reason: '', debt_amount: 0 }
  dialogVisible.value = true
}

const handleSave = async () => {
  if (!form.value.plate_number.trim()) {
    ElMessage.warning('请输入车牌号')
    return
  }

  saving.value = true
  try {
    const res = editingId.value
      ? await updateBlacklist(editingId.value, form.value)
      : await createBlacklist(form.value)
    if (res.code === 200) {
      ElMessage.success(editingId.value ? '更新成功' : '已加入黑名单')
      dialogVisible.value = false
      await loadList()
    }
  } finally {
    saving.value = false
  }
}

const handleToggle = async (row, isActive) => {
  const res = await updateBlacklist(row.id, { is_active: isActive })
  if (res.code === 200) {
    ElMessage.success(isActive ? '已启用拦截' : '已解除拦截')
    loadList()
  }
}

const handleDelete = async (id) => {
  await ElMessageBox.confirm('确定删除该黑名单记录吗？', '提示', { type: 'warning' })
  const res = await deleteBlacklist(id)
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
.tip-alert {
  margin-bottom: 16px;
}
</style>
