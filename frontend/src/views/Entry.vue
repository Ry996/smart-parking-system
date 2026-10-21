<template>
  <el-row :gutter="20">
    <el-col :xs="24" :lg="14">
      <el-card shadow="hover">
        <template #header>
          <div class="card-head">
            <el-icon><Aim /></el-icon>
            <span>车牌识别</span>
            <span class="mode-tag" :class="lprMode.mode">{{ lprMode.label }}</span>
          </div>
        </template>

        <div class="recognition-panel">
          <div class="action-row">
            <el-button type="primary" plain @click="toggleCamera">
              {{ cameraActive ? "关闭摄像头" : "开启摄像头" }}
            </el-button>
            <el-button type="success" :disabled="!cameraReady" :loading="recognizing" @click="captureFromCamera">
              抓拍识别
            </el-button>
          </div>

          <div v-if="cameraActive" class="camera-panel">
            <video ref="videoRef" autoplay playsinline muted class="camera-video"></video>
            <div class="camera-guide">
              <div class="guide-box"></div>
              <div class="guide-tip">请将车牌对准取景框并尽量靠近镜头</div>
            </div>
          </div>

          <el-upload
            class="upload-box"
            drag
            :show-file-list="false"
            :auto-upload="false"
            accept="image/*"
            :on-change="handleImageChange"
          >
            <div class="upload-content">
              <div class="upload-title">上传车牌图片</div>
              <div class="upload-desc">支持图片上传识别，也可先开启摄像头后抓拍识别。</div>
            </div>
          </el-upload>

          <el-alert
            :title="lprMode.mode === 'mock' ? '当前为模拟识别模式，结果会随机生成，不用于真实识别。' : '识别失败时可直接切换到手动录入，不会影响入场登记。'"
            :type="lprMode.mode === 'mock' ? 'warning' : 'info'"
            :closable="false"
          />

          <div v-if="recognitionResult.plate" class="recognition-result success">
            <div class="result-label">识别结果</div>
            <div class="plate-number">{{ recognitionResult.plate }}</div>
            <div class="result-meta">
              车牌类型：{{ plateTypeMap[recognitionResult.plate_type] || recognitionResult.plate_type }}
              <span class="split">|</span>
              置信度：{{ (recognitionResult.confidence * 100).toFixed(2) }}%
            </div>
          </div>

          <div v-if="recognitionError" class="recognition-result error">
            {{ recognitionError }}
          </div>
        </div>
      </el-card>
    </el-col>

    <el-col :xs="24" :lg="10">
      <el-card shadow="hover">
        <template #header>
          <div class="card-head">
            <el-icon><EditPen /></el-icon>
            <span>入场登记</span>
          </div>
        </template>

        <el-form :model="form" label-width="88px">
          <el-form-item label="录入方式">
            <el-radio-group v-model="form.entry_method">
              <el-radio-button value="recognize">图片识别</el-radio-button>
              <el-radio-button value="manual">手动录入</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="车牌号">
            <el-input v-model="form.plate_number" placeholder="请输入车牌号" />
          </el-form-item>
          <el-form-item label="车牌类型">
            <el-select v-model="form.plate_type" style="width: 100%">
              <el-option label="蓝牌" value="blue" />
              <el-option label="黄牌" value="yellow" />
              <el-option label="新能源" value="green" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="submitting" @click="submitEntry">确认入场</el-button>
            <el-button @click="resetForm">重置</el-button>
          </el-form-item>
        </el-form>

        <el-alert
          type="info"
          :closable="false"
          show-icon
          title="系统自动校验：黑名单车辆将被拦截；预约时段内车辆优先放行；月租车辆自动识别并标记。"
          class="entry-tip"
        />
      </el-card>
    </el-col>
  </el-row>

  <el-card shadow="hover" class="table-card">
    <template #header>
      <div class="card-head">
        <el-icon><Van /></el-icon>
        <span>当前在场车辆</span>
      </div>
    </template>
    <el-table :data="parkedList" stripe v-loading="tableLoading">
      <el-table-column prop="plate_number" label="车牌号" width="160" />
      <el-table-column prop="plate_type" label="车牌类型" width="120">
        <template #default="{ row }">{{ plateTypeMap[row.plate_type] || row.plate_type }}</template>
      </el-table-column>
      <el-table-column prop="entry_time" label="入场时间" width="180" />
      <el-table-column label="停车时长">
        <template #default="{ row }">{{ formatDuration(row.entry_time) }}</template>
      </el-table-column>
      <el-table-column prop="remark" label="备注" show-overflow-tooltip />
    </el-table>

    <el-pagination
      v-model:current-page="page"
      :page-size="10"
      :total="total"
      layout="total, prev, pager, next"
      class="pager"
      @current-change="loadParked"
    />
  </el-card>
</template>

<script setup>
import { nextTick, onMounted, onUnmounted, ref } from "vue"
import { ElMessage } from "element-plus"
import { getLprMode, getParkedList, recognizePlate, vehicleEnter } from "../api"

const plateTypeMap = {
  blue: "蓝牌",
  yellow: "黄牌",
  green: "新能源",
}

const form = ref({
  plate_number: "",
  plate_type: "blue",
  entry_method: "manual",
})
const recognitionResult = ref({})
const recognitionError = ref("")
const submitting = ref(false)
const recognizing = ref(false)
const tableLoading = ref(false)
const parkedList = ref([])
const page = ref(1)
const total = ref(0)
const lprMode = ref({ mode: "unknown", label: "识别模式未知" })
const cameraActive = ref(false)
const cameraReady = ref(false)
const videoRef = ref(null)
let cameraStream = null

const runRecognition = async (file) => {
  recognitionError.value = ""
  recognitionResult.value = {}
  form.value.entry_method = "recognize"
  recognizing.value = true

  const formData = new FormData()
  formData.append("image", file)

  try {
    const res = await recognizePlate(formData)
    if (res.code === 200) {
      recognitionResult.value = res.data
      form.value.plate_number = res.data.plate
      form.value.plate_type = res.data.plate_type || "blue"
      ElMessage.success(`识别成功：${res.data.plate}`)
    }
  } catch (error) {
    const msg = error.response?.data?.msg || "识别失败，请改用手动录入。"
    recognitionError.value = msg
    form.value.entry_method = "manual"
  } finally {
    recognizing.value = false
  }
}

const handleImageChange = async (uploadFile) => {
  const file = uploadFile.raw
  if (!file) return
  await runRecognition(file)
}

const startCamera = async () => {
  if (cameraActive.value) return
  try {
    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "environment" },
      audio: false,
    })
    cameraActive.value = true
    cameraReady.value = false
    await nextTick()

    const video = videoRef.value
    if (!video) {
      throw new Error("摄像头预览元素未创建")
    }

    video.srcObject = cameraStream
    await new Promise((resolve) => {
      let settled = false
      const markReady = async () => {
        if (settled) return
        settled = true
        try {
          await video.play()
        } catch {}
        cameraReady.value = true
        resolve()
      }
      video.onloadedmetadata = markReady
      video.oncanplay = markReady
      setTimeout(markReady, 1200)
    })
  } catch (error) {
    stopCamera()
    ElMessage.error("无法打开摄像头，请检查浏览器权限。")
  }
}

const stopCamera = () => {
  if (cameraStream) {
    cameraStream.getTracks().forEach((track) => track.stop())
    cameraStream = null
  }
  if (videoRef.value) {
    videoRef.value.srcObject = null
  }
  cameraActive.value = false
  cameraReady.value = false
}

const toggleCamera = async () => {
  if (cameraActive.value) {
    stopCamera()
  } else {
    await startCamera()
  }
}

const captureFromCamera = async () => {
  if (!videoRef.value) return
  const video = videoRef.value
  if (!cameraReady.value) {
    await new Promise((resolve) => setTimeout(resolve, 600))
  }
  const width = video.videoWidth
  const height = video.videoHeight
  if (!width || !height) {
    ElMessage.warning("摄像头画面尚未准备好，请等待 1 秒后重试")
    return
  }

  const crop = getCropRect(width, height)
  const canvas = document.createElement("canvas")
  canvas.width = crop.width
  canvas.height = crop.height
  const context = canvas.getContext("2d")
  context.drawImage(
    video,
    crop.x,
    crop.y,
    crop.width,
    crop.height,
    0,
    0,
    crop.width,
    crop.height
  )

  const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.95))
  if (!blob) {
    ElMessage.error("抓拍失败，请重试")
    return
  }

  const file = new File([blob], "camera-capture.jpg", { type: "image/jpeg" })
  await runRecognition(file)
}

const getCropRect = (width, height) => {
  const cropWidth = Math.floor(width * 0.46)
  const cropHeight = Math.floor(height * 0.18)
  const x = Math.floor((width - cropWidth) / 2)
  const y = Math.floor(height * 0.53 - cropHeight / 2)
  return {
    x: Math.max(x, 0),
    y: Math.max(y, 0),
    width: Math.min(cropWidth, width),
    height: Math.min(cropHeight, height),
  }
}

const submitEntry = async () => {
  if (!form.value.plate_number.trim()) {
    ElMessage.warning("请输入车牌号")
    return
  }

  submitting.value = true
  try {
    const res = await vehicleEnter({
      plate_number: form.value.plate_number.trim().toUpperCase(),
      plate_type: form.value.plate_type,
      entry_method: form.value.entry_method,
    })
    if (res.code === 200) {
      const remark = res.data?.remark || ""
      if (remark.includes("预约车辆")) {
        ElMessage.success("入场成功（预约车辆，已优先放行）")
      } else if (remark.includes("月租车辆")) {
        ElMessage.success("入场成功（月租车辆）")
      } else {
        ElMessage.success("入场登记成功")
      }
      resetForm()
      loadParked()
    }
  } finally {
    submitting.value = false
  }
}

const resetForm = () => {
  form.value = {
    plate_number: "",
    plate_type: "blue",
    entry_method: "manual",
  }
  recognitionResult.value = {}
  recognitionError.value = ""
}

const loadParked = async () => {
  tableLoading.value = true
  try {
    const res = await getParkedList({ page: page.value, per_page: 10 })
    if (res.code === 200) {
      parkedList.value = res.data.items || []
      total.value = res.data.total || 0
    }
  } finally {
    tableLoading.value = false
  }
}

const loadLprMode = async () => {
  try {
    const res = await getLprMode()
    if (res.code === 200 && res.data) {
      lprMode.value = res.data
    }
  } catch {
    lprMode.value = { mode: "unknown", label: "识别模式未知" }
  }
}

const formatDuration = (entryTime) => {
  if (!entryTime) return "-"
  const diff = Date.now() - new Date(entryTime).getTime()
  const minutes = Math.max(Math.floor(diff / 60000), 0)
  const hours = Math.floor(minutes / 60)
  const remain = minutes % 60
  return hours > 0 ? `${hours}小时${remain}分钟` : `${remain}分钟`
}

onMounted(() => {
  loadParked()
  loadLprMode()
})
onUnmounted(stopCamera)
</script>

<style scoped>
.card-head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.recognition-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.action-row {
  display: flex;
  gap: 12px;
}

.camera-panel {
  position: relative;
  border-radius: 14px;
  overflow: hidden;
  background: #0f172a;
}

.camera-video {
  display: block;
  width: 100%;
  max-height: 360px;
  object-fit: cover;
}

.camera-guide {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.guide-box {
  position: absolute;
  left: 27%;
  top: 44%;
  width: 46%;
  height: 18%;
  border: 3px solid rgba(56, 189, 248, 0.95);
  border-radius: 16px;
  box-shadow: 0 0 0 9999px rgba(15, 23, 42, 0.25);
}

.guide-tip {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 18px;
  text-align: center;
  color: #e2e8f0;
  font-size: 14px;
  text-shadow: 0 1px 2px rgba(15, 23, 42, 0.7);
}

.upload-box {
  width: 100%;
}

.upload-content {
  padding: 24px 12px;
}

.upload-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-1);
}

.upload-desc {
  margin-top: 8px;
  color: var(--text-3);
}

.recognition-result {
  border-radius: 14px;
  padding: 18px;
}

.recognition-result.success {
  background: rgba(16, 185, 129, 0.12);
  border: 1px solid rgba(52, 211, 153, 0.3);
}

.recognition-result.error {
  background: rgba(248, 113, 113, 0.12);
  border: 1px solid rgba(248, 113, 113, 0.3);
  color: #fca5a5;
}

.result-label {
  font-size: 13px;
  color: var(--text-2);
}

.mode-tag {
  display: inline-flex;
  align-items: center;
  margin-left: 10px;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}

.mode-tag.real {
  color: #6ee7b7;
  background: rgba(16, 185, 129, 0.15);
}

.mode-tag.mock {
  color: #fcd34d;
  background: rgba(245, 158, 11, 0.15);
}

.mode-tag.unknown {
  color: #94a3b8;
  background: rgba(100, 116, 139, 0.18);
}

.plate-number {
  margin-top: 10px;
  font-size: 34px;
  font-weight: 700;
  color: #7dd3fc;
  letter-spacing: 2px;
}

.result-meta {
  margin-top: 10px;
  color: var(--text-2);
}

.split {
  margin: 0 8px;
}

.table-card {
  margin-top: 20px;
}

.entry-tip {
  margin-top: 12px;
}

.pager {
  margin-top: 16px;
  justify-content: flex-end;
}
</style>
