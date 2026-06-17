<template>
  <div>
    <el-row justify="space-between" align="middle" style="margin-bottom: 20px">
      <h2 style="margin: 0">Dashboard — 词根校验概览</h2>
      <el-button type="primary" size="large" :loading="running" @click="openRunner">
        {{ running ? '执行中...' : '一键执行全部' }}
      </el-button>
    </el-row>

    <!-- 统计卡片 -->
    <el-row :gutter="16">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-num">{{ stats.total_sources }}</div>
          <div class="stat-label">总词根数</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-num">{{ stats.total_logs }}</div>
          <div class="stat-label">总执行次数</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-num" :style="{ color: matchColor }">{{ matchPercent }}%</div>
          <div class="stat-label">命中率</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-num">{{ stats.screenshot_ok }}</div>
          <div class="stat-label">截图成功数</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 站点柱状图 + 最近日志 -->
    <el-row :gutter="16" style="margin-top: 20px">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><strong>按站点分布</strong></template>
          <div ref="siteChartRef" style="height: 320px"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><strong>最近执行日志</strong></template>
          <el-table :data="stats.recent_logs" size="small" max-height="320">
            <el-table-column prop="root_word_id" label="ID" width="70" />
            <el-table-column prop="website" label="站点" width="140" show-overflow-tooltip />
            <el-table-column prop="root_word" label="词根" show-overflow-tooltip />
            <el-table-column label="结果" width="80">
              <template #default="{ row }">
                <el-tag :type="row.root_word_type === '0' ? 'success' : 'danger'" size="small">
                  {{ row.root_word_type === '0' ? '命中' : '未命中' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="uptime" label="时间" width="160" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- ═══ 右下角浮动执行面板 ═══ -->
    <div v-if="panelVisible" class="float-panel">
      <el-card shadow="always" :body-style="{ padding: '12px 16px' }">
        <!-- 标题栏 -->
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px">
          <strong>执行进度</strong>
          <div>
            <el-button v-if="!running && progress.done === 0" type="primary" size="small" @click="startRun">开始</el-button>
            <el-button text size="small" @click="panelVisible = false">关闭</el-button>
          </div>
        </div>

        <!-- 总进度 -->
        <div style="margin-bottom: 12px">
          <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 12px">
            <span>总进度</span>
            <span>{{ progress.done }} / {{ progress.total }}</span>
          </div>
          <el-progress :percentage="progressPercent" :status="progressStatus" :stroke-width="10" />
        </div>

        <!-- 迷你统计 -->
        <el-row :gutter="6" style="margin-bottom: 10px">
          <el-col :span="8">
            <div class="micro-stat" style="background: #f0f9ff">
              <div class="micro-num">{{ progress.matched }}</div>
              <div class="micro-label">命中</div>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="micro-stat" style="background: #fff5f5">
              <div class="micro-num" style="color: #f56c6c">{{ progress.unmatched }}</div>
              <div class="micro-label">未命中</div>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="micro-stat" style="background: #f5f7fa">
              <div class="micro-num" style="color: #e6a23c">{{ Math.max(0, progress.total - progress.done) }}</div>
              <div class="micro-label">待执行</div>
            </div>
          </el-col>
        </el-row>

        <!-- 最近几条记录（可滚动） -->
        <div style="max-height: 200px; overflow-y: auto; font-size: 12px">
          <div
            v-for="(item, idx) in progress.items.slice(0, 20)"
            :key="idx"
            style="display: flex; justify-content: space-between; align-items: center; padding: 4px 0; border-bottom: 1px solid #f0f0f0"
          >
            <div>
              <el-tag :type="item.root_word_type === '0' ? 'success' : 'danger'" size="small" style="margin-right: 6px">
                {{ item.root_word_type === '0' ? '命中' : '未命中' }}
              </el-tag>
              <span>ID={{ item.root_word_id }}</span>
            </div>
            <el-link
              v-if="item.check_remark && item.check_remark.startsWith('http')"
              :href="item.check_remark" target="_blank" type="primary" :underline="false"
            >
              截图
            </el-link>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchStats, runProcess, fetchLogs } from '../api'
import * as echarts from 'echarts'

// ── 统计数据 ──
const stats = ref({ total_sources: 0, total_logs: 0, matched_rate: 0, screenshot_ok: 0, by_site: [], recent_logs: [] })
const siteChartRef = ref(null)
let chartInstance = null

const matchPercent = computed(() => (stats.value.matched_rate * 100).toFixed(1))
const matchColor = computed(() => stats.value.matched_rate >= 0.5 ? '#67c23a' : '#e6a23c')

function renderSiteChart() {
  if (!siteChartRef.value) return
  if (chartInstance) chartInstance.dispose()
  chartInstance = echarts.init(siteChartRef.value)
  const sites = stats.value.by_site.map(s => s.website.replace('https://www.amazon.', '').replace('/', ''))
  const matched = stats.value.by_site.map(s => s.matched)
  const unmatched = stats.value.by_site.map(s => s.unmatched)
  chartInstance.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { data: ['命中', '未命中'] },
    grid: { left: 40, right: 20, bottom: 40, top: 20 },
    xAxis: { type: 'category', data: sites, axisLabel: { rotate: 30 } },
    yAxis: { type: 'value' },
    series: [
      { name: '命中', type: 'bar', stack: 'total', data: matched, color: '#67c23a' },
      { name: '未命中', type: 'bar', stack: 'total', data: unmatched, color: '#f56c6c' },
    ],
  })
}

async function loadStats() {
  try {
    const { data } = await fetchStats()
    stats.value = data
    setTimeout(renderSiteChart, 100)
  } catch (e) {
    console.error('Failed to load stats', e)
  }
}

onMounted(loadStats)
watch(() => stats.value.by_site, () => setTimeout(renderSiteChart, 100))

// ── 执行面板 ──
const panelVisible = ref(false)
const running = ref(false)
const progress = ref({ done: 0, total: 0, matched: 0, unmatched: 0, items: [] })
let pollTimer = null

const progressPercent = computed(() => {
  if (progress.value.total === 0) return 0
  return Math.round((progress.value.done / progress.value.total) * 100)
})
const progressStatus = computed(() => {
  if (!running.value && progress.value.done > 0) return 'success'
  return ''
})

function openRunner() {
  panelVisible.value = true
}

async function startRun() {
  running.value = true
  const totalSources = stats.value.total_sources
  const beforeTotal = stats.value.total_logs  // 执行前日志总数
  progress.value = { done: 0, total: totalSources, matched: 0, unmatched: 0, items: [] }

  // 轮询：每 2 秒查日志增量
  pollTimer = setInterval(async () => {
    try {
      const { data: logData } = await fetchLogs({ limit: 20, offset: 0 })
      const added = Math.max(0, logData.total - beforeTotal)
      progress.value.done = Math.min(added, totalSources)
    } catch (e) {
      console.error('Poll error', e)
    }
  }, 2000)

  try {
    const { data } = await runProcess({ limit: 100 })
    clearInterval(pollTimer)

    // 用后端返回的准确结果覆盖
    progress.value.done = data.total
    progress.value.total = data.total
    progress.value.matched = data.matched
    progress.value.unmatched = data.unmatched
    // 取结果详情（有截图链接）
    progress.value.items = data.results
      .filter(r => r.root_word_type !== '-1')  // 过滤异常
      .reverse()  // 最新在上

    ElMessage.success(`执行完成：共 ${data.total} 条，命中 ${data.matched}，未命中 ${data.unmatched}`)
    await loadStats()
  } catch (e) {
    clearInterval(pollTimer)
    ElMessage.error('执行失败：' + (e.response?.data?.detail || e.message))
  } finally {
    running.value = false
  }
}
</script>

<style scoped>
.stat-card { text-align: center; }
.stat-num { font-size: 32px; font-weight: bold; color: #409eff; }
.stat-label { margin-top: 8px; color: #909399; font-size: 14px; }

.float-panel {
  position: fixed;
  right: 24px;
  bottom: 24px;
  width: 360px;
  z-index: 2000;
}
.micro-stat { text-align: center; padding: 6px; border-radius: 4px; }
.micro-num { font-size: 16px; font-weight: bold; color: #409eff; }
.micro-label { font-size: 11px; color: #909399; }
</style>
