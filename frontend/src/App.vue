<template>
  <el-container style="min-height: 100vh">
    <!-- 侧边栏 -->
    <el-aside width="220px" style="background: #1d1e2c; color: #fff">
      <div style="padding: 20px 16px; font-size: 18px; font-weight: bold; border-bottom: 1px solid #333">
        📊 BI 面板
      </div>
      <el-menu
        :default-active="currentRoute"
        background-color="#1d1e2c"
        text-color="#aab"
        active-text-color="#409EFF"
        router
        style="border-right: none"
      >
        <el-menu-item index="/">
          <el-icon><DataAnalysis /></el-icon>
          <span>Dashboard</span>
        </el-menu-item>
        <el-menu-item index="/sources">
          <el-icon><List /></el-icon>
          <span>来源数据</span>
        </el-menu-item>
        <el-menu-item index="/logs">
          <el-icon><Document /></el-icon>
          <span>执行日志</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- 主内容 -->
    <el-main style="background: #f0f2f5; padding: 24px">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { DataAnalysis, List, Document } from '@element-plus/icons-vue'

const route = useRoute()
const currentRoute = computed(() => route.path)
</script>

<style>
body { margin: 0; font-family: 'Helvetica Neue', sans-serif }
</style>
