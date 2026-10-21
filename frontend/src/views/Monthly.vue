<template>
  <div>
    <el-row :gutter="16" class="stat-row">
      <el-col :span="8">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-num active">{{ activeCount }}</div>
            <div class="stat-label">生效中月租车辆</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-num soon">{{ soonCount }}</div>
            <div class="stat-label">7 天内即将到期</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-num expired">{{ expiredCount }}</div>
            <div class="stat-label">已过期月租车辆</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="hover">
      <template #header>
        <div class="header-row">
          <div class="header-title">
            <el-icon><Calendar /></el-icon>
            <span>月租车辆管理</span>
          </div>
          <el-button type="primary" @click="openDialog()">新增月租车辆</el-button>
        </div>
      </template>

      <el-form inline>
        <el-form-item label="关键字">
          <el-input v-model="filters.keyword" placeholder="车牌/车主/电话" clearable style="width: 220px" @keyup.enter="loadList" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" clearable style="width: 140px" @change="loadList">
            <el-option label="生效中" value="active" />
            <el-option label="即将到期" value="soon" />
            <el-option label="已过期" value="expired" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadList">查询</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="list" stripe v-loading="loading">
        <el-table-column prop="plate_number" label="车牌号" width="120" />
        <el-table-column prop="owner_name" label="车主姓名" width="120" />
        <el-table-column prop="phone" label="联系电话" width="140" />
        <el-table-column prop="package_name" label="套餐名称" min-width="130" />
        <el-table-column prop="start_date" label="生效日期" width="110" />
        <el-table-column prop="end_date" label="到期日期" width="110" />
        <el-table-column prop="fee" label="套餐费用" width="100">
          <template #default="{ row }">¥{{ row.fee }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" @click="openRenew(row)">续费</el-button>
            <el-button text type="primary" @click="openDialog(row)">编辑</el-button>
            <el-button text type="danger" @click="handleDelete(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增/编辑 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑月租车辆' : '新增月租车辆'" width="540px">
      <el-form :model="form" label-width="110px">
        <el-form-item label="车牌号">
          <el-input v-model="form.plate_number" placeholder="如 皖A88888" />
        </el-form-item>
        <el-form-item label="车主姓名">
          <el-input v-model="form.owner_name" />
        </el-form-item>
        <el-form-item label="联系电话">
          <el-input v-model="form.phone" />
        </el-form-item>
        <el-form-item label="套餐名称">
          <el-input v-model="form.package_name" placeholder="如 标准月租套餐" />
        </el-form-item>
        <el-form-item label="生效日期">
          <el-date-picker v-model="form.start_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="到期日期">
          <el-date-picker v-model="form.end_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="套餐费用">
          <el-input-number v-model="form.fee" :min="0" :step="50" :precision="2" />
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

    <!-- 续费 -->
    <el-dialog v-model="renewVisible" title="月租续费" width="480px">
      <el-form :model="renewForm" label-width="120px">
        <el-form-item label="车牌号">
          <el-input :model-value="renewForm.plate_number" disabled />
        </el-form-item>
        <el-form-item label="当前到期日">
          <el-input :model-value="renewForm.end_date" disabled />
        </el-form-item>
        <el-form-item label="续费方式">
          <el-radio-group v-model="renewForm.mode">
            <el-radio value="months">按月份顺延</el-radio>
            <el-radio value="date">指定到期日期</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="renewForm.mode === 'months'" label="续费月数">
          <el-input-number v-model="renewForm.months" :min="1" :max="36" />
        </el-form-item>
        <el-form-item v-else label="新到期日期">
          <el-date-picker v-model="renewForm.end_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="续费金额">
          <el-input-number v-model="renewForm.fee" :min="0" :step="50" :precision="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="renewVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleRenew">确认续费</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createMonthly, deleteMonthly, getMonthlyList, renewMonthly, updateMonthly } from '../api'

const list = ref([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const renewVisible = ref(false)
const editingId = ref(null)
const renewForm = ref({ plate_number: '', end_date: '', months: 1, fee: 0, mode: 'months' })
const filters = ref({ keyword: '', status: '' })

const form = ref({
  plate_number: '',
  owner_name: '',
  phone: '',
  package_name: '标准月租套餐',
  start_date: '',
  end_date: '',
  fee: 0,
  remark: '',
})

const activeCount = computed(() => list.value.filter((i) => i.status === 'active').length)
const soonCount = computed(() => list.value.filter((i) => i.status === 'soon').length)
const expiredCount = computed(() => list.value.filter((i) => i.status === 'expired').length)

const statusText = (s) => ({ active: '生效中', soon: '即将到期', expired: '已过期' }[s] || s)
const statusTag = (s) => ({ active: 'success', soon: 'warning', expired: 'danger' }[s] || 'info')

const loadList = async () => {
  loading.value = true
  try {
    const res = await getMonthlyList(filters.value)
    if (res.code === 200) {
      list.value = res.data || []
    }
  } finally {
    loading.value = false
  }
}

const defaultForm = () => ({
  plate_number: '',
  owner_name: '',
  phone: '',
  package_name: '标准月租套餐',
  start_date: '',
  end_date: '',
  fee: 0,
  remark: '',
})

const openDialog = (row = null) => {
  editingId.value = row?.id || null
  form.value = row ? {
    plate_number: row.plate_number,
    owner_name: row.owner_name,
    phone: row.phone,
    package_name: row.package_name,
    start_date: row.start_date,
    end_date: row.end_date,
    fee: row.fee,
    remark: row.remark,
  } : defaultForm()
  dialogVisible.value = true
}

const handleSave = async () => {
  if (!form.value.plate_number.trim()) {
    ElMessage.warning('请输入车牌号')
    return
  }
  if (!form.value.start_date || !form.value.end_date) {
    ElMessage.warning('请选择生效日期和到期日期')
    return
  }

  saving.value = true
  try {
    const res = editingId.value
      ? await updateMonthly(editingId.value, form.value)
      : await createMonthly(form.value)
    if (res.code === 200) {
      ElMessage.success(editingId.value ? '更新成功' : '创建成功')
      dialogVisible.value = false
      await loadList()
    }
  } finally {
    saving.value = false
  }
}

const openRenew = (row) => {
  renewForm.value = {
    id: row.id,
    plate_number: row.plate_number,
    end_date: row.end_date,
    months: 1,
    fee: row.fee,
    mode: 'months',
  }
  renewVisible.value = true
}

const handleRenew = async () => {
  const payload = renewForm.value.mode === 'months'
    ? { months: renewForm.value.months, fee: renewForm.value.fee }
    : { end_date: renewForm.value.end_date, fee: renewForm.value.fee }

  saving.value = true
  try {
    const res = await renewMonthly(renewForm.value.id, payload)
    if (res.code === 200) {
      ElMessage.success('续费成功')
      renewVisible.value = false
      await loadList()
    }
  } finally {
    saving.value = false
  }
}

const handleDelete = async (id) => {
  await ElMessageBox.confirm('确定删除该月租车辆吗？', '提示', { type: 'warning' })
  const res = await deleteMonthly(id)
  if (res.code === 200) {
    ElMessage.success('删除成功')
    loadList()
  }
}

onMounted(loadList)
</script>

<style scoped>
.stat-row {
  margin-bottom: 16px;
}
.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
}
.stat-num {
  font-size: 32px;
  font-weight: 700;
}
.stat-num.active { color: #16a34a; }
.stat-num.soon { color: #f59e0b; }
.stat-num.expired { color: #dc2626; }
.stat-label {
  color: #64748b;
  font-size: 14px;
}
.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>
