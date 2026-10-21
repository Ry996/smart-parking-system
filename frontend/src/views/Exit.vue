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
            drag
            :show-file-list="false"
            :auto-upload="false"
            accept="image/*"
            :on-change="handleImageChange"
          >
            <div class="upload-content">
              <div class="upload-title">上传离场车牌图片</div>
              <div class="upload-desc">支持图片上传识别，也可先开启摄像头后抓拍识别。</div>
            </div>
          </el-upload>

          <el-alert
            :title="lprMode.mode === 'mock' ? '当前为模拟识别模式，结果会随机生成，不用于真实识别。' : '识别失败时可直接改为手动录入。'"
            :type="lprMode.mode === 'mock' ? 'warning' : 'info'"
            :closable="false"
          />

          <div v-if="recognitionResult.plate" class="recognition-result">
            <div class="plate-number">{{ recognitionResult.plate }}</div>
            <div class="result-meta">识别方式：图片识别</div>
          </div>

          <el-alert v-if="recognitionError" :title="recognitionError" type="error" :closable="false" />
        </div>
      </el-card>
    </el-col>

    <el-col :xs="24" :lg="10">
      <el-card shadow="hover">
        <template #header>
          <div class="card-head">
            <el-icon><Money /></el-icon>
            <span>离场预览</span>
          </div>
        </template>

        <el-form :model="form" label-width="88px">
          <el-form-item label="录入方式">
            <el-radio-group v-model="form.exit_method">
              <el-radio-button value="recognize">图片识别</el-radio-button>
              <el-radio-button value="manual">手动录入</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="车牌号">
            <el-input v-model="form.plate_number" placeholder="请输入车牌号" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="previewLoading" @click="loadPreview">查询预览</el-button>
          </el-form-item>
        </el-form>

        <div v-if="previewData" class="preview-box">
          <div class="preview-row"><span>车牌号</span><strong>{{ previewData.record.plate_number }}</strong></div>
          <div class="preview-row"><span>入场时间</span><strong>{{ previewData.record.entry_time }}</strong></div>
          <div class="preview-row"><span>停车时长</span><strong>{{ previewData.duration_text }}</strong></div>
          <div class="preview-row"><span>应收金额</span><strong class="money">¥{{ Number(previewData.fee).toFixed(2) }}</strong></div>

          <el-alert
            v-if="previewData.is_monthly"
            type="success"
            :closable="false"
            show-icon
            class="monthly-tip"
            title="月租车辆：套餐内离场不额外收费"
          />

          <div class="preview-actions">
            <el-button type="warning" :loading="submitting" @click="submitExit(false)">
              {{ previewData.is_monthly ? "月租车辆免费放行" : "确认收费离场" }}
            </el-button>
            <el-button v-if="userStore.isAdmin && !previewData.is_monthly" :loading="submitting" @click="submitExit(true)">管理员免费放行</el-button>
          </div>
        </div>
      </el-card>
    </el-col>
  </el-row>

  <!-- 模拟在线支付窗口 -->
  <el-dialog v-model="payDialogVisible" title="扫码支付（演示环境模拟）" width="420px" :close-on-click-modal="false">
    <div class="pay-body">
      <div class="pay-row"><span>车牌号</span><strong>{{ pendingPay.plate }}</strong></div>
      <div class="pay-row"><span>停车费用</span><strong class="pay-money">¥{{ pendingPay.fee.toFixed(2) }}</strong></div>
      <div class="pay-qr">
        <canvas ref="qrCanvasRef" width="180" height="180"></canvas>
        <div class="qr-tip">请使用微信 / 支付宝扫码支付</div>
      </div>
      <el-button type="success" class="pay-btn" :loading="paying" @click="handlePayConfirm">
        模拟支付成功并放行
      </el-button>
    </div>
  </el-dialog>
</template>

<script setup>
import { nextTick, onUnmounted, ref } from "vue"
import { ElMessage } from "element-plus"
import { getLprMode, payRecord, previewExit, recognizePlate, vehicleExit } from "../api"
import { useUserStore } from "../store/user"

const userStore = useUserStore()
const form = ref({
  plate_number: "",
  exit_method: "manual",
})
const recognitionResult = ref({})
const recognitionError = ref("")
const previewData = ref(null)
const previewLoading = ref(false)
const submitting = ref(false)
const recognizing = ref(false)
const lprMode = ref({ mode: "unknown", label: "识别模式未知" })
const cameraActive = ref(false)
const cameraReady = ref(false)
const videoRef = ref(null)
let cameraStream = null

// 模拟在线支付状态
const payDialogVisible = ref(false)
const pendingPay = ref({ plate: "", fee: 0, recordId: null })
const paying = ref(false)
const qrCanvasRef = ref(null)

// 绘制模拟二维码（演示用，非真实二维码）
const drawMockQr = () => {
  const canvas = qrCanvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext("2d")
  const size = 8
  const count = 180 / size
  ctx.fillStyle = "#ffffff"
  ctx.fillRect(0, 0, 180, 180)
  ctx.fillStyle = "#0f172a"
  const corners = [
    [0, 0],
    [count - 7, 0],
    [0, count - 7],
  ]
  for (const [cx, cy] of corners) {
    ctx.fillRect(cx * size, cy * size, 7 * size, 7 * size)
    ctx.fillStyle = "#ffffff"
    ctx.fillRect((cx + 1.5) * size, (cy + 1.5) * size, 4 * size, 4 * size)
    ctx.fillStyle = "#0f172a"
    ctx.fillRect((cx + 2.5) * size, (cy + 2.5) * size, 2 * size, 2 * size)
  }
  let seed = 7
  const rand = () => (seed = (seed * 9301 + 49297) % 233280) / 233280
  for (let y = 0; y < count; y++) {
    for (let x = 0; x < count; x++) {
      const inCorner = corners.some(([cx, cy]) => x >= cx && x < cx + 7 && y >= cy && y < cy + 7)
      if (!inCorner && rand() > 0.52) ctx.fillRect(x * size, y * size, size, size)
    }
  }
}

const resetExitForm = () => {
  form.value = { plate_number: "", exit_method: "manual" }
  recognitionResult.value = {}
  recognitionError.value = ""
  previewData.value = null
}

const runRecognition = async (file) => {
  recognitionError.value = ""
  recognitionResult.value = {}
  form.value.exit_method = "recognize"
  recognizing.value = true

  const formData = new FormData()
  formData.append("image", file)

  try {
    const res = await recognizePlate(formData)
    if (res.code === 200) {
      recognitionResult.value = res.data
      form.value.plate_number = res.data.plate
      await loadPreview()
    }
  } catch (error) {
    recognitionError.value = error.response?.data?.msg || "识别失败，请改用手动录入。"
    form.value.exit_method = "manual"
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

const loadPreview = async () => {
  if (!form.value.plate_number.trim()) {
    ElMessage.warning("请输入车牌号")
    return
  }

  previewLoading.value = true
  previewData.value = null
  try {
    const res = await previewExit({
      plate_number: form.value.plate_number.trim().toUpperCase(),
    })
    if (res.code === 200) {
      previewData.value = res.data
    }
  } finally {
    previewLoading.value = false
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

const submitExit = async (isFreeRelease) => {
  if (!previewData.value) {
    ElMessage.warning("请先查询离场预览")
    return
  }

  submitting.value = true
  try {
    const res = await vehicleExit({
      plate_number: form.value.plate_number.trim().toUpperCase(),
      exit_method: form.value.exit_method,
      is_free_release: isFreeRelease,
    })
    if (res.code === 200) {
      const data = res.data || {}
      if (data.need_pay) {
        // 应收离场：弹出模拟支付窗口
        pendingPay.value = {
          plate: data.plate_number,
          fee: Number(data.fee || 0),
          recordId: data.id,
        }
        payDialogVisible.value = true
        await nextTick()
        drawMockQr()
      } else {
        ElMessage.success(data.is_monthly ? "月租车辆放行成功，套餐内免费" : (isFreeRelease ? "已免费放行" : "离场结算成功"))
        resetExitForm()
      }
    }
  } finally {
    submitting.value = false
  }
}

const handlePayConfirm = async () => {
  paying.value = true
  try {
    const res = await payRecord(pendingPay.value.recordId)
    if (res.code === 200) {
      ElMessage.success("支付成功，车辆已放行")
      payDialogVisible.value = false
      resetExitForm()
    }
  } finally {
    paying.value = false
  }
}

loadLprMode()
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
  background: rgba(56, 189, 248, 0.1);
  border: 1px solid rgba(56, 189, 248, 0.25);
}

.plate-number {
  font-size: 34px;
  font-weight: 700;
  color: #7dd3fc;
}

.result-meta {
  margin-top: 10px;
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

.preview-box {
  margin-top: 10px;
  border-radius: 16px;
  background: rgba(251, 191, 36, 0.08);
  border: 1px solid rgba(251, 191, 36, 0.2);
  padding: 18px;
}

.preview-row {
  display: flex;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid rgba(251, 191, 36, 0.15);
  color: var(--text-2);
}

.preview-row:last-of-type {
  border-bottom: none;
}

.money {
  color: #fcd34d;
  font-size: 24px;
}

.monthly-tip {
  margin-top: 12px;
}

.preview-actions {
  margin-top: 18px;
  display: flex;
  gap: 12px;
}

.pay-body {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.pay-row {
  width: 100%;
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid rgba(148, 163, 184, 0.16);
  color: var(--text-2);
}

.pay-money {
  color: #34d399;
  font-size: 22px;
}

.pay-qr {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 12px;
  border: 1px dashed rgba(148, 163, 184, 0.3);
  border-radius: 12px;
}

.qr-tip {
  color: var(--text-3);
  font-size: 13px;
}

.pay-btn {
  width: 100%;
}
</style>
