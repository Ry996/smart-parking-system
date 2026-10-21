<template>
  <el-card shadow="hover">
    <template #header>
      <div class="header-row">
        <div class="header-title">
          <el-icon><PriceTag /></el-icon>
          <span>收费规则管理</span>
        </div>
        <el-button type="primary" @click="openDialog()">新增规则</el-button>
      </div>
    </template>

    <el-table :data="rules" stripe v-loading="loading">
      <el-table-column prop="rule_name" label="规则名称" />
      <el-table-column prop="fee_type" label="收费方式" width="120">
        <template #default="{ row }">{{ row.fee_type === 'hourly' ? '按小时收费' : '按次收费' }}</template>
      </el-table-column>
      <el-table-column label="收费标准">
        <template #default="{ row }">
          <span v-if="row.fee_type === 'hourly'">¥{{ row.price_per_hour }}/小时</span>
          <span v-else>¥{{ row.flat_price }}/次</span>
        </template>
      </el-table-column>
      <el-table-column prop="free_minutes" label="免费时长" width="120">
        <template #default="{ row }">{{ row.free_minutes }} 分钟</template>
      </el-table-column>
      <el-table-column prop="max_daily" label="单日封顶" width="120">
        <template #default="{ row }">{{ row.max_daily ? `¥${row.max_daily}` : '-' }}</template>
      </el-table-column>
      <el-table-column prop="is_active" label="状态" width="100">
        <template #default="{ row }">{{ row.is_active ? '启用' : '停用' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="180">
        <template #default="{ row }">
          <el-button text type="primary" @click="openDialog(row)">编辑</el-button>
          <el-button text type="danger" @click="handleDelete(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <el-dialog v-model="dialogVisible" :title="editingId ? '编辑规则' : '新增规则'" width="520px">
    <el-form :model="form" label-width="110px">
      <el-form-item label="规则名称">
        <el-input v-model="form.rule_name" />
      </el-form-item>
      <el-form-item label="收费方式">
        <el-radio-group v-model="form.fee_type">
          <el-radio value="hourly">按小时收费</el-radio>
          <el-radio value="flat">按次收费</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="免费时长">
        <el-input-number v-model="form.free_minutes" :min="0" :step="5" />
      </el-form-item>
      <el-form-item v-if="form.fee_type === 'hourly'" label="每小时金额">
        <el-input-number v-model="form.price_per_hour" :min="0" :step="0.5" :precision="2" />
      </el-form-item>
      <el-form-item v-else label="按次金额">
        <el-input-number v-model="form.flat_price" :min="0" :step="1" :precision="2" />
      </el-form-item>
      <el-form-item label="单日封顶">
        <el-input-number v-model="form.max_daily" :min="0" :step="1" :precision="2" />
      </el-form-item>
      <el-form-item label="是否启用">
        <el-switch v-model="form.is_active" :active-value="1" :inactive-value="0" />
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
import { createFeeRule, deleteFeeRule, getFeeRules, updateFeeRule } from '../api'

const rules = ref([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editingId = ref(null)
const form = ref({
  rule_name: '',
  vehicle_type: 'all',
  fee_type: 'hourly',
  free_minutes: 15,
  price_per_hour: 5,
  flat_price: 10,
  max_daily: 50,
  is_active: 1,
})

const defaultForm = () => ({
  rule_name: '',
  vehicle_type: 'all',
  fee_type: 'hourly',
  free_minutes: 15,
  price_per_hour: 5,
  flat_price: 10,
  max_daily: 50,
  is_active: 1,
})

const loadRules = async () => {
  loading.value = true
  try {
    const res = await getFeeRules()
    if (res.code === 200) {
      rules.value = res.data || []
    }
  } finally {
    loading.value = false
  }
}

const openDialog = (row = null) => {
  editingId.value = row?.id || null
  form.value = row ? { ...row } : defaultForm()
  dialogVisible.value = true
}

const handleSave = async () => {
  if (!form.value.rule_name.trim()) {
    ElMessage.warning('请输入规则名称')
    return
  }

  saving.value = true
  try {
    const res = editingId.value
      ? await updateFeeRule(editingId.value, form.value)
      : await createFeeRule(form.value)

    if (res.code === 200) {
      ElMessage.success(editingId.value ? '规则更新成功' : '规则创建成功')
      dialogVisible.value = false
      await loadRules()
    }
  } finally {
    saving.value = false
  }
}

const handleDelete = async (id) => {
  await ElMessageBox.confirm('确定删除该收费规则吗？', '提示', { type: 'warning' })
  const res = await deleteFeeRule(id)
  if (res.code === 200) {
    ElMessage.success('删除成功')
    loadRules()
  }
}

onMounted(loadRules)
</script>

<style scoped>
.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>
