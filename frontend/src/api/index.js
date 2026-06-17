import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1/root-word',
  timeout: 30000,
})

// ---------- 统计数据 ----------
export function fetchStats() {
  return api.get('/stats')
}

// ---------- 一键执行 ----------
export function runProcess({ limit = 100, root_word_ids = '' } = {}) {
  const params = { limit }
  if (root_word_ids) params.root_word_ids = root_word_ids
  return api.post('/process', null, { params })
}

// ---------- 来源数据（root_word_check）----------
export function fetchSources({ limit = 20, offset = 0 } = {}) {
  return api.get('/source', { params: { limit, offset } })
}

// ---------- 执行日志（root_word_check_log）----------
export function fetchLogs({ root_word_id, root_word, website, site_name, root_word_type, sort, limit = 20, offset = 0 } = {}) {
  const params = { limit, offset }
  if (root_word_id) params.root_word_id = root_word_id
  if (root_word) params.root_word = root_word
  if (website) params.website = website
  if (site_name) params.site_name = site_name
  if (sort) params.sort = sort
  if (root_word_type !== '' && root_word_type !== null && root_word_type !== undefined) {
    params.root_word_type = root_word_type
  }
  return api.get('/logs', { params })
}
