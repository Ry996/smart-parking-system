<template>
  <div class="big-screen">
    <!-- 顶部标题栏 -->
    <div class="screen-header">
      <div class="header-title">
        <span class="title-mark"></span>
        <span>智慧停车场运营中心</span>
        <span class="title-sub">Smart Parking Operation Center</span>
      </div>
      <div class="header-right">
        <span class="mode-chip" :class="lprMode.mode">{{ lprMode.label }}</span>
        <span class="clock">{{ nowText }}</span>
      </div>
    </div>

    <!-- 核心指标 -->
    <div class="metric-row">
      <div class="metric-card">
        <div class="metric-label">今日入场车辆</div>
        <div class="metric-value accent-cyan">{{ overview.today_count }}</div>
        <div class="metric-note">当天入场登记累计</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">当前在场车辆</div>
        <div class="metric-value accent-yellow">{{ overview.parked_now }}</div>
        <div class="metric-note">占用车位实时数量</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">今日停车收入</div>
        <div class="metric-value accent-green">¥{{ overview.today_income.toFixed(2) }}</div>
        <div class="metric-note">按已离场订单统计</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">可用车位</div>
        <div class="metric-value accent-purple">{{ overview.available_spaces }}<span class="unit">/{{ overview.total_spaces }}</span></div>
        <div class="metric-note">占用率 {{ occupancy }}%</div>
      </div>
    </div>

    <!-- 中部图表区 -->
    <div class="chart-row">
      <div class="chart-col col-left">
        <div class="panel">
          <div class="panel-title">车位占用率</div>
          <div ref="gaugeRef" class="gauge-box"></div>
        </div>
        <div class="panel">
          <div class="panel-title">车位实时分布</div>
          <div class="space-grid">
            <div v-for="cell in gridCells" :key="cell.id" class="space-cell" :class="cell.type" :title="cell.title"></div>
          </div>
          <div class="legend-row">
            <span class="legend-item"><i class="dot free"></i>可用 {{ spaces.available }}</span>
            <span class="legend-item"><i class="dot reserved"></i>预约 {{ reservedCount }}</span>
            <span class="legend-item"><i class="dot occupied"></i>占用 {{ spaces.occupied }}</span>
          </div>
        </div>
      </div>

      <div class="chart-col col-middle">
        <div class="panel fill">
          <div class="panel-title">近 7 天车流趋势</div>
          <div ref="flowChartRef" class="chart-box"></div>
        </div>
      </div>

      <div class="chart-col col-right">
        <div class="panel fill">
          <div class="panel-title">近 7 天收入统计</div>
          <div ref="incomeChartRef" class="chart-box"></div>
        </div>
        <div class="panel">
          <div class="panel-title">在场车辆（实时）</div>
          <div class="parked-list">
            <div v-for="row in parkedVehicles" :key="row.id" class="parked-item">
              <span class="parked-plate">{{ row.plate_number }}</span>
              <span class="parked-time">{{ formatDuration(row.entry_time) }}</span>
            </div>
            <div v-if="!parkedVehicles.length" class="parked-empty">当前无在场车辆</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from "vue"
import * as echarts from "echarts"
import { getFlowStats, getIncomeStats, getLprMode, getOverview, getParkedList, getReservations, getSpaces } from "../api"

const overview = ref({ today_count: 0, today_income: 0, parked_now: 0, total_spaces: 0, available_spaces: 0 })
const spaces = ref({ total: 0, available: 0, occupied: 0 })
const reservedCount = ref(0)
const parkedVehicles = ref([])
const lprMode = ref({ mode: "unknown", label: "识别模式未知" })
const nowText = ref("")
const flowChartRef = ref(null)
const incomeChartRef = ref(null)
const gaugeRef = ref(null)

const occupancy = computed(() => {
  const total = overview.value.total_spaces
  return total ? Math.round((overview.value.parked_now / total) * 100) : 0
})

const gridCells = computed(() => {
  const cells = []
  const total = Math.max(spaces.value.total, 1)
  const occupied = Math.min(spaces.value.occupied, total)
  const reserved = Math.min(reservedCount.value, Math.max(total - occupied, 0))
  for (let i = 0; i < occupied; i++) cells.push({ id: `o-${i}`, type: "occupied", title: `车位 ${i + 1}：已占用` })
  for (let i = 0; i < reserved; i++) cells.push({ id: `r-${i}`, type: "reserved", title: `车位 ${occupied + i + 1}：预约预留` })
  for (let i = cells.length; i < total; i++) cells.push({ id: `f-${i}`, type: "free", title: `车位 ${i + 1}：空闲` })
  return cells
})

let flowChart, incomeChart, gaugeChart, clockTimer

const formatDuration = (entryTime) => {
  if (!entryTime) return "-"
  const diff = Date.now() - new Date(entryTime).getTime()
  const minutes = Math.max(Math.floor(diff / 60000), 0)
  const hours = Math.floor(minutes / 60)
  const remain = minutes % 60
  return hours > 0 ? `${hours}小时${remain}分` : `${remain}分钟`
}

const startClock = () => {
  const pad = (n) => String(n).padStart(2, "0")
  const update = () => {
    const d = new Date()
    nowText.value = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  }
  update()
  clockTimer = setInterval(update, 1000)
}

const loadData = async () => {
  const [overviewRes, parkedRes, spacesRes, reservationRes, flowRes, incomeRes, modeRes] = await Promise.all([
    getOverview(), getParkedList({ page: 1, per_page: 8 }), getSpaces(), getReservations(),
    getFlowStats({ period: "week" }), getIncomeStats(), getLprMode(),
  ])
  if (overviewRes.code === 200) overview.value = overviewRes.data
  if (parkedRes.code === 200) parkedVehicles.value = parkedRes.data.items || []
  if (spacesRes.code === 200 && spacesRes.data) spaces.value = spacesRes.data
  if (reservationRes.code === 200) {
    const now = Date.now()
    reservedCount.value = (reservationRes.data || []).filter(
      (r) => r.status === "pending" && new Date(r.end_time).getTime() >= now
    ).length
  }
  if (modeRes.code === 200) lprMode.value = modeRes.data

  if (flowRes.code === 200) {
    flowChart.setOption({
      tooltip: { trigger: "axis", backgroundColor: "#1e293b", textStyle: { color: "#e2e8f0" } },
      xAxis: { type: "category", data: flowRes.data.labels, axisLabel: { color: "#94a3b8" }, axisLine: { lineStyle: { color: "#334155" } } },
      yAxis: { type: "value", name: "车次", nameTextStyle: { color: "#94a3b8" }, axisLabel: { color: "#94a3b8" }, splitLine: { lineStyle: { color: "#1e293b" } } },
      series: [{
        type: "line", smooth: true, data: flowRes.data.counts,
        areaStyle: { color: "rgba(56,189,248,0.25)" },
        itemStyle: { color: "#38bdf8" },
        lineStyle: { width: 3 },
      }],
      grid: { top: 30, right: 20, bottom: 30, left: 50 },
    })
  }
  if (incomeRes.code === 200) {
    incomeChart.setOption({
      tooltip: { trigger: "axis", backgroundColor: "#1e293b", textStyle: { color: "#e2e8f0" } },
      xAxis: { type: "category", data: incomeRes.data.labels, axisLabel: { color: "#94a3b8" }, axisLine: { lineStyle: { color: "#334155" } } },
      yAxis: { type: "value", name: "金额", nameTextStyle: { color: "#94a3b8" }, axisLabel: { color: "#94a3b8" }, splitLine: { lineStyle: { color: "#1e293b" } } },
      series: [{
        type: "bar", data: incomeRes.data.incomes, barWidth: 16,
        itemStyle: { color: "#f59e0b", borderRadius: [6, 6, 0, 0] },
      }],
      grid: { top: 30, right: 20, bottom: 30, left: 50 },
    })
  }

  const rate = overview.value.total_spaces ? Math.min(overview.value.parked_now / overview.value.total_spaces, 1) : 0
  gaugeChart.setOption({
    series: [{
      type: "gauge",
      startAngle: 210, endAngle: -30,
      min: 0, max: 100,
      progress: { show: true, width: 14, itemStyle: { color: rate >= 0.85 ? "#f87171" : rate >= 0.6 ? "#fbbf24" : "#34d399" } },
      axisLine: { lineStyle: { width: 14, color: [[1, "#1e293b"]] } },
      axisTick: { show: false }, splitLine: { show: false }, axisLabel: { show: false }, pointer: { show: false },
      anchor: { show: false },
      detail: {
        valueAnimation: true, offsetCenter: [0, 0],
        fontSize: 34, fontWeight: 700, color: "#e2e8f0",
        formatter: (v) => `${Math.round(v)}%`,
      },
      title: { offsetCenter: [0, 46], fontSize: 14, color: "#94a3b8" },
      data: [{ value: Math.round(rate * 100), name: "车位占用率" }],
    }],
  })
}

const resizeHandler = () => {
  flowChart?.resize()
  incomeChart?.resize()
  gaugeChart?.resize()
}

onMounted(async () => {
  startClock()
  await nextTick()
  flowChart = echarts.init(flowChartRef.value)
  incomeChart = echarts.init(incomeChartRef.value)
  gaugeChart = echarts.init(gaugeRef.value)
  await loadData()
  window.addEventListener("resize", resizeHandler)
})

onUnmounted(() => {
  clearInterval(clockTimer)
  window.removeEventListener("resize", resizeHandler)
  flowChart?.dispose()
  incomeChart?.dispose()
  gaugeChart?.dispose()
})
</script>

<style scoped>
.big-screen {
  margin: -24px;
  padding: 22px 24px;
  min-height: calc(100vh - 40px);
  background: radial-gradient(1200px 500px at 20% -10%, #12314f 0%, transparent 60%),
              radial-gradient(1000px 500px at 110% 20%, #14244a 0%, transparent 55%),
              linear-gradient(160deg, #0b1220 0%, #0d1b2e 100%);
  color: #e2e8f0;
  font-family: "PingFang SC", "Microsoft YaHei", sans-serif;
}

.screen-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.25);
}

.header-title {
  display: flex;
  align-items: baseline;
  gap: 14px;
  font-size: 26px;
  font-weight: 800;
  letter-spacing: 2px;
  background: linear-gradient(90deg, #38bdf8, #818cf8);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.title-mark {
  width: 6px;
  height: 26px;
  border-radius: 3px;
  background: linear-gradient(180deg, #38bdf8, #818cf8);
  align-self: center;
}

.title-sub {
  font-size: 13px;
  font-weight: 400;
  color: #64748b;
  letter-spacing: 1px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 14px;
}

.mode-chip {
  padding: 3px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}

.mode-chip.real { color: #6ee7b7; background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.4); }
.mode-chip.mock { color: #fcd34d; background: rgba(245, 158, 11, 0.15); border: 1px solid rgba(245, 158, 11, 0.4); }
.mode-chip.unknown { color: #94a3b8; background: rgba(100, 116, 139, 0.15); border: 1px solid rgba(100, 116, 139, 0.4); }

.clock {
  font-size: 18px;
  font-weight: 600;
  color: #cbd5e1;
  font-variant-numeric: tabular-nums;
}

.metric-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin: 16px 0;
}

.metric-card {
  background: linear-gradient(145deg, rgba(30, 58, 95, 0.55), rgba(15, 30, 55, 0.65));
  border: 1px solid rgba(56, 189, 248, 0.18);
  border-radius: 14px;
  padding: 18px 20px;
}

.metric-label { font-size: 14px; color: #94a3b8; }
.metric-value { margin-top: 10px; font-size: 34px; font-weight: 800; font-variant-numeric: tabular-nums; }
.metric-value .unit { font-size: 16px; color: #64748b; margin-left: 4px; }
.metric-note { margin-top: 8px; font-size: 12px; color: #64748b; }

.accent-cyan { color: #38bdf8; }
.accent-yellow { color: #fbbf24; }
.accent-green { color: #34d399; }
.accent-purple { color: #a78bfa; }

.chart-row {
  display: grid;
  grid-template-columns: 300px 1fr 300px;
  gap: 16px;
}

.chart-col {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.panel {
  background: linear-gradient(160deg, rgba(23, 42, 74, 0.6), rgba(13, 27, 46, 0.7));
  border: 1px solid rgba(148, 163, 184, 0.15);
  border-radius: 14px;
  padding: 14px 16px;
}

.panel.fill { flex: 1; }

.panel-title {
  font-size: 15px;
  font-weight: 700;
  color: #e2e8f0;
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.panel-title::before {
  content: "";
  width: 4px;
  height: 14px;
  border-radius: 2px;
  background: #38bdf8;
}

.gauge-box { height: 210px; }
.chart-box { height: 260px; }

.space-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(14px, 1fr));
  gap: 5px;
}

.space-cell { height: 14px; border-radius: 3px; }
.space-cell.free { background: rgba(52, 211, 153, 0.75); }
.space-cell.reserved { background: rgba(251, 191, 36, 0.85); }
.space-cell.occupied { background: rgba(248, 113, 113, 0.8); }

.legend-row {
  display: flex;
  gap: 14px;
  margin-top: 12px;
  font-size: 12px;
  color: #94a3b8;
}

.legend-item { display: inline-flex; align-items: center; gap: 6px; }
.dot { width: 9px; height: 9px; border-radius: 2px; display: inline-block; }
.dot.free { background: #34d399; }
.dot.reserved { background: #fbbf24; }
.dot.occupied { background: #f87171; }

.parked-list {
  max-height: 210px;
  overflow-y: auto;
}

.parked-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 9px 6px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.12);
}

.parked-plate { font-weight: 700; color: #fcd34d; letter-spacing: 1px; }
.parked-time { color: #94a3b8; font-size: 12px; }
.parked-empty { color: #64748b; text-align: center; padding: 24px 0; font-size: 13px; }

.parked-list::-webkit-scrollbar { width: 6px; }
.parked-list::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
</style>
