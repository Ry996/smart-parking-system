<template>
  <div class="assistant-page">
    <el-card shadow="hover">
      <template #header>
        <div class="header-row">
          <div class="header-title">
            <el-icon><ChatDotRound /></el-icon>
            <span>AI 知识库问答（RAG）</span>
          </div>
          <div class="status-row">
            <el-tag :type="status.enabled ? 'success' : 'info'" effect="dark" size="small">
              {{ status.enabled ? "DeepSeek 在线" : "离线抽取模式" }}
            </el-tag>
            <el-tag type="info" size="small">
              知识库 {{ status.knowledge?.documents || 0 }} 篇 /
              {{ status.knowledge?.chunks || 0 }} 片段
            </el-tag>
            <el-tag size="small" effect="plain">{{ status.promptVersions?.rag_answer || "rag-v2" }}</el-tag>
          </div>
        </div>
      </template>

      <div class="ask-row">
        <el-input
          v-model="question"
          type="textarea"
          :rows="3"
          maxlength="300"
          show-word-limit
          resize="none"
          placeholder="请输入与停车场业务相关的问题，例如：停车 20 分钟要收多少钱？"
          @keydown.enter.exact.prevent="ask"
        />
        <div class="ask-actions">
          <div class="samples">
            <el-tag
              v-for="sample in samples"
              :key="sample"
              class="sample-tag"
              effect="plain"
              @click="question = sample"
            >
              {{ sample }}
            </el-tag>
          </div>
          <el-button type="primary" :loading="loading" :disabled="!question.trim()" @click="ask">
            提问
          </el-button>
        </div>
      </div>
    </el-card>

    <el-card v-if="result" shadow="hover" class="answer-card">
      <template #header>
        <div class="header-row">
          <div class="header-title">
            <el-icon><Cpu /></el-icon>
            <span>回答</span>
          </div>
          <div class="status-row">
            <el-tag :type="modeTagType" effect="dark" size="small">{{ result.mode }}</el-tag>
            <el-tag type="info" size="small">来源 {{ result.provider }}</el-tag>
            <el-tag v-if="result.basedOnSources" type="success" size="small" effect="plain">有资料依据</el-tag>
            <el-tag v-else type="warning" size="small" effect="plain">无资料依据</el-tag>
            <el-button size="small" :icon="Warning" @click="openFeedback">举报为幻觉</el-button>
          </div>
        </div>
      </template>

      <el-alert
        v-if="result.blocked"
        type="error"
        :closable="false"
        show-icon
        title="请求已被安全策略拦截"
        :description="'命中规则：' + (result.reasons || []).join('、')"
      />
      <el-alert
        v-else-if="result.refused"
        type="warning"
        :closable="false"
        show-icon
        title="资料不足，模型拒绝编造答案"
      />

      <div class="answer-text">{{ result.answer }}</div>

      <template v-if="result.sources && result.sources.length">
        <el-divider content-position="left">引用来源</el-divider>
        <div class="source-list">
          <div v-for="source in result.sources" :key="source.index" class="source-item">
            <div class="source-head">
              <el-tag size="small" effect="plain">[{{ source.index }}]</el-tag>
              <span class="source-title">{{ source.title }}</span>
              <span class="source-meta">{{ source.locator }}</span>
              <span class="source-meta">相似度 {{ source.score }}</span>
              <span class="source-meta">覆盖 {{ source.coverage }}</span>
            </div>
            <div class="source-excerpt">{{ source.excerpt }}…</div>
          </div>
        </div>
      </template>
      <el-empty v-else description="本次回答没有命中知识库片段（走的是通用知识兜底）" :image-size="70" />
    </el-card>

    <el-dialog v-model="feedbackVisible" title="登记 AI 复核案例" width="560px">
      <el-form label-width="90px">
        <el-form-item label="问题">
          <el-input v-model="feedback.question" type="textarea" :rows="2" disabled />
        </el-form-item>
        <el-form-item label="问题类型">
          <el-select v-model="feedback.category" style="width: 100%">
            <el-option
              v-for="(label, code) in status.categories || {}"
              :key="code"
              :label="label"
              :value="code"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="期望答案">
          <el-input v-model="feedback.expected_answer" type="textarea" :rows="2" placeholder="正确结果是什么，便于后续对比" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="feedback.note" maxlength="200" placeholder="例如：模型未扣减免费时长" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="feedbackVisible = false">取消</el-button>
        <el-button type="primary" :loading="feedbackLoading" @click="submitFeedback">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue"
import { ElMessage } from "element-plus"
import { askAi, getAiStatus, submitAiFeedback } from "../api"

const samples = [
  "停车 20 分钟要收多少钱？",
  "月租车辆离场怎么收费？",
  "黑名单车辆能入场吗？",
  "车位满了还能进场吗？",
]

const question = ref("")
const loading = ref(false)
const result = ref(null)
const status = ref({ enabled: false, knowledge: {}, promptVersions: {}, categories: {} })

const feedbackVisible = ref(false)
const feedbackLoading = ref(false)
const feedback = reactive({
  question: "",
  category: "hallucination",
  expected_answer: "",
  note: "",
})

const modeTagType = {
  RAG: "success",
  GENERAL: "warning",
  BLOCKED: "danger",
}

const loadStatus = async () => {
  try {
    const res = await getAiStatus()
    if (res.code === 200) {
      status.value = res.data
    }
  } catch (error) {
    // 状态加载失败不影响提问
  }
}

const ask = async () => {
  const text = question.value.trim()
  if (!text || loading.value) return

  loading.value = true
  try {
    const res = await askAi({ question: text })
    if (res.code === 200) {
      result.value = res.data
    }
  } finally {
    loading.value = false
  }
}

const openFeedback = () => {
  if (!result.value) return
  feedback.question = result.value.question || question.value
  feedback.category = result.value.refused ? "refusal" : "hallucination"
  feedback.expected_answer = ""
  feedback.note = ""
  feedbackVisible.value = true
}

const submitFeedback = async () => {
  feedbackLoading.value = true
  try {
    const res = await submitAiFeedback({
      question: feedback.question,
      answer: result.value?.answer || "",
      category: feedback.category,
      expected_answer: feedback.expected_answer,
      note: feedback.note,
      mode: result.value?.mode || "",
    })
    if (res.code === 200) {
      ElMessage.success("案例已记录，可用于实验报告的幻觉案例分析")
      feedbackVisible.value = false
    }
  } finally {
    feedbackLoading.value = false
  }
}

onMounted(loadStatus)
</script>

<style scoped>
.assistant-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 700;
  color: #e2e8f0;
}

.status-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.ask-row {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.ask-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.samples {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.sample-tag {
  cursor: pointer;
}

.answer-card {
  margin-bottom: 10px;
}

.answer-text {
  white-space: pre-line;
  line-height: 1.9;
  color: #cbd5e1;
  font-size: 14px;
}

.source-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.source-item {
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(15, 30, 51, 0.7);
  border: 1px solid rgba(148, 163, 184, 0.14);
}

.source-head {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.source-title {
  color: #cfefff;
  font-weight: 600;
  font-size: 13px;
}

.source-meta {
  color: #64748b;
  font-size: 12px;
}

.source-excerpt {
  margin-top: 6px;
  color: #94a3b8;
  font-size: 12px;
  line-height: 1.7;
}
</style>
