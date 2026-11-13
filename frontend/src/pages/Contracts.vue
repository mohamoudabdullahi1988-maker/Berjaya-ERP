<script setup>
import { onMounted, ref } from 'vue'
import { apiGet } from '../api'
import { CONTRACT, statusText, textValue } from '../contracts'
import '../contracts.css'
const rows = ref([]), query = ref(''), loading = ref(false), error = ref(''), page = ref(0), more = ref(false)
let request = 0
async function load(next = 0) {
  const id = ++request
  loading.value = true; error.value = ''; rows.value = []
  try {
    const result = await apiGet(CONTRACT, { fields: ['name', 'customer', 'docstatus'], or_filters: query.value.trim() ? [['name', 'like', `%${query.value.trim()}%`], ['customer', 'like', `%${query.value.trim()}%`]] : undefined, limit_start: next * 25, limit_page_length: 25, order_by: 'modified desc' })
    if (!Array.isArray(result.data)) throw new Error('Unexpected contracts response.')
    // Read each permitted document to obtain its child unit rows; no unrestricted child query.
    const documents = await Promise.all(result.data.map(row => apiGet(`${CONTRACT}/${encodeURIComponent(row.name)}`)))
    if (id !== request) return
    rows.value = documents.map(r => r.data); page.value = next; more.value = result.data.length === 25
  } catch (e) { if (id === request) error.value = e.kind === 'denied' ? 'You do not have permission to read these contracts.' : e.message }
  finally { if (id === request) loading.value = false }
}
onMounted(() => load())
</script>
<template>
  <section class="contract-page">
    <h1>Contracts</h1>
    <form @submit.prevent="load()"><label for="contract-search">Reference or customer</label><input id="contract-search" v-model="query" type="search"><button type="submit" :disabled="loading">Search</button></form>
    <p v-if="loading" role="status">Loading contracts…</p>
    <p v-else-if="error" role="alert">{{ error }}</p>
    <template v-else>
      <p v-if="!rows.length">No contracts found.</p>
      <div v-else class="table-scroll"><table><caption>Saved contracts</caption><thead><tr><th>Reference</th><th>Customer</th><th>Property</th><th>Status</th></tr></thead><tbody><tr v-for="row in rows" :key="row.name"><td><RouterLink :to="{ name: 'contract-detail', params: { name: row.name } }">{{ row.name }}</RouterLink></td><td>{{ textValue(row.customer) }}</td><td>{{ Array.isArray(row.units) ? row.units.map(u => textValue(u.unit)).join(', ') || 'None recorded' : 'Unavailable' }}</td><td>{{ statusText(row.docstatus) }}</td></tr></tbody></table></div>
      <button v-if="page" @click="load(page - 1)">Previous</button><button v-if="more" @click="load(page + 1)">Next</button>
    </template>
  </section>
</template>
