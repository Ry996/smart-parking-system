<template>
  <el-row :gutter="20">
    <el-col :xs="24" :lg="12">
      <el-card shadow="hover">
        <template #header>
          <div class="header-title">
            <el-icon><Grid /></el-icon>
            <span>车位概览</span>
          </div>
        </template>
        <div class="space-panel">
          <el-progress type="dashboard" :percentage="usageRate" :width="220" />
          <div class="space-summary">
            <div>总车位：{{ spaceData.total }}</div>
            <div>已占用：{{ spaceData.occupied }}</div>
            <div>可用车位：{{ spaceData.available }}</div>
          </div>
        </div>
      </el-card>
    </el-col>

    <el-col :xs="24" :lg="12">
      <el-card shadow="hover">
        <template #header>
          <div class="header-title">
            <el-icon><Setting /></el-icon>
            <span>车位配置</span>
          </div>
        </template>
        <el-form label-width="100px">
          <el-form-item label="总车位数">
            <el-input-number v-model="form.total" :min="1" :max="10000" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="saving" @click="handleSave">保存配置</el-button>
            <el-button @click="loadData">刷新数据</el-button>
          </el-form-item>
        </el-form>
      </el-card>
    </el-col>
  </el-row>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getSpaces, updateSpaces } from '../api'

const spaceData = ref({
  total: 0,
  available: 0,
  occupied: 0,
})
const form = ref({ total: 100 })
const saving = ref(false)

const usageRate = computed(() => {
  if (!spaceData.value.total) return 0
  return Math.round((spaceData.value.occupied / spaceData.value.total) * 100)
})

const loadData = async () => {
  const res = await getSpaces()
  if (res.code === 200) {
    spaceData.value = res.data
    form.value.total = res.data.total
  }
}

const handleSave = async () => {
  saving.value = true
  try {
    const res = await updateSpaces({ total: form.value.total })
    if (res.code === 200) {
      ElMessage.success('车位配置已更新')
      await loadData()
    }
  } finally {
    saving.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.space-panel {
  display: flex;
  align-items: center;
  gap: 36px;
  justify-content: center;
  min-height: 320px;
}

.space-summary {
  line-height: 2.2;
  font-size: 16px;
  color: var(--text-2);
}
</style>
