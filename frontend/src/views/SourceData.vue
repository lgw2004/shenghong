<template>
  <div>
    <h2 style="margin-bottom: 20px">来源数据 — root_word_check</h2>

    <!-- 筛选栏 -->
    <el-card shadow="never" style="margin-bottom: 16px">
      <el-form :inline="true" :model="filters">
        <el-form-item label="站点">
          <el-select v-model="filters.site" placeholder="全部" clearable style="width: 200px" @change="load">
            <el-option v-for="s in siteSet" :key="s" :label="s" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input v-model="filters.keyword" placeholder="搜索词根/关键词" clearable style="width: 220px" @keyup.enter="load" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="load">查询</el-button>
          <el-button @click="filters = { site: '', keyword: '' }; load()">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 数据表格 -->
    <el-card shadow="never">
      <el-table :data="tableData" v-loading="loading" stripe max-height="560">
        <el-table-column prop="root_word_id" label="ID" width="80" />
        <el-table-column prop="site_name" label="站点" width="80" />
        <el-table-column prop="root_word" label="词根" min-width="160" show-overflow-tooltip />
        <el-table-column prop="keywords" label="关键词" min-width="220" show-overflow-tooltip />
        <el-table-column prop="website" label="网址" min-width="200" show-overflow-tooltip />
        <el-table-column prop="uptime" label="更新时间" width="170" />
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
import { ref, computed, onMounted } from 'vue'
import { fetchSources } from '../api'

const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const filters = ref({ site: '', keyword: '' })
const pagination = ref({ page: 1, size: 20 })
const allSources = ref([])   // 全量数据（前端分页+筛选）

const siteSet = computed(() => [...new Set(allSources.value.map(r => r.site_name).filter(Boolean))])

async function load() {
  loading.value = true
  try {
    // 先拉全量（量不大时前端筛选足够）
    const { data } = await fetchSources({ limit: 500, offset: 0 })
    allSources.value = data.items

    // 筛选
    let filtered = [...allSources.value]
    if (filters.value.site) {
      filtered = filtered.filter(r => r.site_name === filters.value.site)
    }
    if (filters.value.keyword) {
      const kw = filters.value.keyword.toLowerCase()
      filtered = filtered.filter(r =>
        (r.root_word || '').toLowerCase().includes(kw) ||
        (r.keywords || '').toLowerCase().includes(kw)
      )
    }

    total.value = filtered.length
    const start = (pagination.value.page - 1) * pagination.value.size
    tableData.value = filtered.slice(start, start + pagination.value.size)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
