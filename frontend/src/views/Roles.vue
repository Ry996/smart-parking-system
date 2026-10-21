<template>
  <div class="roles-page">
    <el-row :gutter="20">
      <el-col :xs="24" :lg="9">
        <el-card shadow="hover">
          <template #header>
            <div class="header-row">
              <div class="header-title">
                <el-icon><Lock /></el-icon>
                <span>角色列表</span>
              </div>
              <div class="header-actions">
                <el-button size="small" @click="load">刷新</el-button>
                <el-button size="small" type="primary" @click="openCreate">新建角色</el-button>
              </div>
            </div>
          </template>

          <el-table
            :data="roles"
            highlight-current-row
            size="small"
            @current-change="selectRole"
          >
            <el-table-column prop="name" label="角色" width="110">
              <template #default="{ row }">
                <span class="role-name">{{ row.name }}</span>
                <el-tag v-if="row.is_builtin" size="small" type="info" effect="plain">内置</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="code" label="编码" width="100" />
            <el-table-column label="权限数" width="80" align="center">
              <template #default="{ row }">{{ row.permissions.length }}</template>
            </el-table-column>
            <el-table-column label="用户数" width="80" align="center">
              <template #default="{ row }">{{ row.user_count }}</template>
            </el-table-column>
            <el-table-column label="操作" width="80" align="center">
              <template #default="{ row }">
                <el-button
                  v-if="!row.is_builtin"
                  link
                  type="danger"
                  size="small"
                  @click.stop="removeRole(row)"
                >
                  删除
                </el-button>
                <span v-else class="muted">—</span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="15">
        <el-card shadow="hover">
          <template #header>
            <div class="header-row">
              <div class="header-title">
                <el-icon><Key /></el-icon>
                <span>权限矩阵{{ selectedRole ? " · " + selectedRole.name : "" }}</span>
              </div>
              <el-button
                size="small"
                type="primary"
                :loading="saving"
                :disabled="!selectedRole"
                @click="savePermissions"
              >
                保存权限
              </el-button>
            </div>
          </template>

          <el-empty v-if="!selectedRole" description="先在左侧选择一个角色" :image-size="80" />

          <el-checkbox-group v-else v-model="selectedPermissions" class="permission-groups">
            <div v-for="group in catalog.groups" :key="group.group" class="permission-group">
              <div class="group-title">{{ group.group }}</div>
              <div class="group-items">
                <el-checkbox
                  v-for="item in group.items"
                  :key="item.code"
                  :value="item.code"
                  class="permission-item"
                >
                  <span class="permission-name">{{ item.name }}</span>
                  <span class="permission-code">{{ item.code }}</span>
                </el-checkbox>
              </div>
            </div>
          </el-checkbox-group>

          <el-alert
            v-if="selectedRole && selectedRole.code === 'admin'"
            class="tip"
            type="warning"
            :closable="false"
            show-icon
            title="管理员角色必须保留 role:manage 权限，内置角色不可删除。"
          />
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="createVisible" title="新建自定义角色" width="460px">
      <el-form label-width="80px">
        <el-form-item label="角色编码">
          <el-input v-model="createForm.code" placeholder="例如 auditor，仅字母数字下划线" />
        </el-form-item>
        <el-form-item label="角色名称">
          <el-input v-model="createForm.name" placeholder="例如 审计员" />
        </el-form-item>
        <el-form-item label="角色说明">
          <el-input v-model="createForm.description" placeholder="该角色负责什么" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="submitCreate">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue"
import { ElMessage, ElMessageBox } from "element-plus"
import {
  createRole,
  deleteRole,
  getPermissionCatalog,
  getRoles,
  updateRolePermissions,
} from "../api"

const roles = ref([])
const catalog = ref({ groups: [] })
const selectedId = ref(null)
const selectedPermissions = ref([])
const saving = ref(false)

const createVisible = ref(false)
const creating = ref(false)
const createForm = reactive({ code: "", name: "", description: "" })

const selectedRole = computed(() => roles.value.find((item) => item.id === selectedId.value) || null)

const load = async () => {
  const [roleRes, catalogRes] = await Promise.all([getRoles(), getPermissionCatalog()])
  if (roleRes.code === 200) {
    roles.value = roleRes.data
    const keep = roles.value.find((item) => item.id === selectedId.value)
    if (keep) {
      selectedPermissions.value = [...keep.permissions]
    }
  }
  if (catalogRes.code === 200) {
    catalog.value = catalogRes.data
  }
}

const selectRole = (row) => {
  if (!row) return
  selectedId.value = row.id
  selectedPermissions.value = [...row.permissions]
}

const savePermissions = async () => {
  if (!selectedRole.value) return
  saving.value = true
  try {
    const res = await updateRolePermissions(selectedRole.value.id, selectedPermissions.value)
    if (res.code === 200) {
      ElMessage.success("权限已更新，重新登录或刷新后生效")
      await load()
    }
  } finally {
    saving.value = false
  }
}

const openCreate = () => {
  createForm.code = ""
  createForm.name = ""
  createForm.description = ""
  createVisible.value = true
}

const submitCreate = async () => {
  if (!createForm.code || !createForm.name) {
    ElMessage.warning("角色编码和名称不能为空")
    return
  }
  creating.value = true
  try {
    const res = await createRole({ ...createForm })
    if (res.code === 200) {
      ElMessage.success("角色已创建")
      createVisible.value = false
      await load()
    }
  } finally {
    creating.value = false
  }
}

const removeRole = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除角色「${row.name}」吗？`, "提示", { type: "warning" })
  } catch (error) {
    return
  }
  const res = await deleteRole(row.id)
  if (res.code === 200) {
    ElMessage.success("角色已删除")
    if (selectedId.value === row.id) {
      selectedId.value = null
      selectedPermissions.value = []
    }
    await load()
  }
}

onMounted(load)
</script>

<style scoped>
.roles-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 700;
  color: #e2e8f0;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.role-name {
  margin-right: 6px;
  color: #cbd5e1;
  font-weight: 600;
}

.muted {
  color: #475569;
}

.permission-groups {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.permission-group {
  padding: 12px 14px;
  border-radius: 10px;
  background: rgba(15, 30, 51, 0.62);
  border: 1px solid rgba(148, 163, 184, 0.12);
}

.group-title {
  font-size: 13px;
  font-weight: 700;
  color: #7dd3fc;
  margin-bottom: 10px;
}

.group-items {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 18px;
}

.permission-item {
  margin-right: 0;
}

.permission-name {
  color: #cbd5e1;
  font-size: 13px;
}

.permission-code {
  margin-left: 6px;
  color: #64748b;
  font-size: 11px;
  font-family: Consolas, monospace;
}

.tip {
  margin-top: 14px;
}
</style>
