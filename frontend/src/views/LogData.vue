<template>
  <div>
    <h2 style="margin-bottom: 20px">执行日志 — root_word_check_log</h2>

    <!-- 筛选栏 -->
    <el-card shadow="never" style="margin-bottom: 16px">
      <el-form :inline="true" :model="filters">
        <el-form-item label="词根ID">
          <el-input v-model="filters.root_word_id" placeholder="如 100" clearable style="width: 140px" @keyup.enter="load" />
        </el-form-item>
        <el-form-item label="词根">
          <el-input v-model="filters.root_word" placeholder="模糊搜索" clearable style="width: 160px" @keyup.enter="load" />
        </el-form-item>
        <el-form-item label="站点网址">
          <el-input v-model="filters.website" placeholder="如 amazon.com" clearable style="width: 180px" @keyup.enter="load" />
        </el-form-item>
        <el-form-item label="站点名">
          <el-input v-model="filters.site_name" placeholder="如 美国" clearable style="width: 140px" @keyup.enter="load" />
        </el-form-item>
        <el-form-item label="命中类型">
          <el-select v-model="filters.root_word_type" placeholder="全部" clearable style="width: 120px" @change="load">
            <el-option label="全部" value="" />
            <el-option label="命中" value="0" />
            <el-option label="未命中" value="1" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="load">查询</el-button>
          <el-button @click="filters = { root_word_id: '', root_word: '', website: '', site_name: '', root_word_type: '' }; load()">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 数据表格 -->
    <el-card shadow="never">
      <el-table :data="tableData" v-loading="loading" stripe max-height="560">
        <el-table-column prop="id" label="日志ID" width="80" />
        <el-table-column prop="root_word_id" label="词根ID" width="90" />
        <el-table-column prop="site_name" label="站点名" width="80" />
        <el-table-column prop="website" label="站点网址" width="180" show-overflow-tooltip />
        <el-table-column prop="root_word" label="词根" min-width="140" show-overflow-tooltip />
        <el-table-column label="结果" width="80">
          <template #default="{ row }">
            <el-tag :type="row.root_word_type === '0' ? 'success' : 'danger'" size="small">
              {{ row.root_word_type === '0' ? '命中' : '未命中' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="截图" width="100">
          <template #default="{ row }">
            <a v-if="row.check_remark && row.check_remark.startsWith('http')"
               :href="row.check_remark" target="_blank" style="color: #409eff">查看截图</a>
            <span v-else-if="row.check_remark === 'screenshot failed'" style="color: #f56c6c">截图失败</span>
            <span v-else style="color: #909399">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="uptime" label="时间" width="170" />
      </el-table>
      <div style="margin-top: 16px; text-align: right">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.size"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @size-change="load"
          @current-change="load"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { fetchLogs } from '../api'

const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const filters = ref({ root_word_id: '', root_word: '', website: '', site_name: '', root_word_type: '' })
const pagination = ref({ page: 1, size: 20 })

async function load() {
  loading.value = true
  try {
    const params = {
      limit: pagination.value.size,
      offset: (pagination.value.page - 1) * pagination.value.size,
    }
    if (filters.value.root_word_id) params.root_word_id = Number(filters.value.root_word_id)
    if (filters.value.root_word) params.root_word = filters.value.root_word
    if (filters.value.website) params.website = filters.value.website
    if (filters.value.site_name) params.site_name = filters.value.site_name
    if (filters.value.root_word_type !== '') params.root_word_type = filters.value.root_word_type

    const { data } = await fetchLogs(params)
    tableData.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
