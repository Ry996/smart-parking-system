<template>
  <el-card shadow="hover">
    <template #header>
      <div class="header-row">
        <div class="header-title">
          <el-icon><UserFilled /></el-icon>
          <span>用户管理</span>
        </div>
        <el-button type="primary" @click="openDialog()">新增用户</el-button>
      </div>
    </template>

    <el-table :data="users" stripe v-loading="loading">
      <el-table-column prop="username" label="用户名" />
      <el-table-column prop="real_name" label="姓名" />
      <el-table-column prop="role" label="角色" width="120">
        <template #default="{ row }">{{ row.role === 'admin' ? '管理员' : '操作员' }}</template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="120">
        <template #default="{ row }">{{ row.status ? '启用' : '禁用' }}</template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="180" />
      <el-table-column label="操作" width="180">
        <template #default="{ row }">
          <el-button text type="primary" @click="openDialog(row)">编辑</el-button>
          <el-button text type="danger" @click="handleDelete(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <el-dialog v-model="dialogVisible" :title="editingId ? '编辑用户' : '新增用户'" width="480px">
    <el-form :model="form" label-width="88px">
      <el-form-item label="用户名">
        <el-input v-model="form.username" :disabled="Boolean(editingId)" />
      </el-form-item>
      <el-form-item label="姓名">
        <el-input v-model="form.real_name" />
      </el-form-item>
      <el-form-item label="角色">
        <el-radio-group v-model="form.role">
          <el-radio value="admin">管理员</el-radio>
          <el-radio value="operator">操作员</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="状态">
        <el-switch v-model="form.status" :active-value="1" :inactive-value="0" />
      </el-form-item>
      <el-form-item label="密码">
        <el-input v-model="form.password" type="password" show-password :placeholder="editingId ? '留空则不修改' : '请输入登录密码'" />
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
import { createUser, deleteUser, getUsers, updateUser } from '../api'

const users = ref([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editingId = ref(null)
const form = ref({
  username: '',
  real_name: '',
  role: 'operator',
  status: 1,
  password: '',
})

const loadUsers = async () => {
  loading.value = true
  try {
    const res = await getUsers()
    if (res.code === 200) {
      users.value = res.data || []
    }
  } finally {
    loading.value = false
  }
}

const openDialog = (row = null) => {
  editingId.value = row?.id || null
  form.value = row
    ? { username: row.username, real_name: row.real_name, role: row.role, status: row.status, password: '' }
    : { username: '', real_name: '', role: 'operator', status: 1, password: '' }
  dialogVisible.value = true
}

const handleSave = async () => {
  if (!form.value.username.trim()) {
    ElMessage.warning('请输入用户名')
    return
  }

  saving.value = true
  try {
    const payload = { ...form.value, username: form.value.username.trim() }
    const res = editingId.value
      ? await updateUser(editingId.value, payload)
      : await createUser(payload)

    if (res.code === 200) {
      ElMessage.success(editingId.value ? '用户更新成功' : '用户创建成功')
      dialogVisible.value = false
      await loadUsers()
    }
  } finally {
    saving.value = false
  }
}

const handleDelete = async (id) => {
  await ElMessageBox.confirm('确定删除该用户吗？', '提示', { type: 'warning' })
  const res = await deleteUser(id)
  if (res.code === 200) {
    ElMessage.success('删除成功')
    loadUsers()
  }
}

onMounted(loadUsers)
</script>

<style scoped>
.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>
