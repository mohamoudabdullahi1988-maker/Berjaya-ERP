<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { apiGet } from '../api'
import { CONTRACT, fileLink, money, numeric, statusText, textValue, timeline } from '../contracts'
import WorkflowPanel from '../components/WorkflowPanel.vue'
import '../contracts.css'
const route = useRoute(), doc = ref(null), flow = ref(null), loading = ref(false), error = ref(''), flowLoading = ref(false), flowError = ref('')
let request = 0, flowRequest = 0
const restricted = computed(() => !flow.value || flowLoading.value || !!flowError.value || flow.value.stages.some(s => (s.figures && Object.values(s.figures).includes('unavailable'))))
const displayMoney = value => restricted.value ? 'Unavailable' : money(value, doc.value?.currency)
const difference = computed(() => !restricted.value && numeric(doc.value?.amount_due) && numeric(doc.value?.schedule_total) ? Math.round((doc.value.amount_due - doc.value.schedule_total) * 100) / 100 : null)
async function refreshWorkflow() {
  if (!doc.value) return
  const id = ++flowRequest, name = doc.value.name
  flowLoading.value = true; flow.value = null; flowError.value = ''
  try { const result = await timeline(name); if (id === flowRequest) flow.value = result }
  catch (e) { if (id === flowRequest) { flowError.value = e.kind === 'denied' ? 'You do not have permission to read this workflow.' : e.message; if (e.kind === 'denied') { doc.value = null; error.value = flowError.value } } }
  finally { if (id === flowRequest) flowLoading.value = false }
}
async function load() {
  const id = ++request; ++flowRequest
  doc.value = null; flow.value = null; flowError.value = ''; flowLoading.value = false; loading.value = true; error.value = ''
  try {
    const result = await apiGet(`${CONTRACT}/${encodeURIComponent(route.params.name)}`)
    if (!result.data?.name) throw new Error('Unexpected contract response.')
    if (id !== request) return
    doc.value = result.data
    await refreshWorkflow()
  } catch (e) { if (id === request) error.value = e.kind === 'denied' ? 'You do not have permission to read this contract.' : e.message }
  finally { if (id === request) loading.value = false }
}
watch(() => route.params.name, load, { immediate: true })
onMounted(() => window.addEventListener('focus', refreshWorkflow))
onBeforeUnmount(() => { ++request; ++flowRequest; window.removeEventListener('focus', refreshWorkflow) })
</script>
<template>
  <section class="contract-page">
    <nav aria-label="Breadcrumb"><RouterLink :to="{ name: 'contracts' }">Contracts</RouterLink></nav>
    <p v-if="loading" role="status">Loading contract…</p>
    <p v-else-if="error" role="alert">{{ error }}</p>
    <template v-else-if="doc">
      <header><h1>{{ doc.name }}</h1><span>{{ statusText(doc.docstatus) }}</span></header>
      <div class="contract-cards">
        <article><h2>Buyer</h2><p>{{ textValue(doc.customer) }}</p></article>
        <article><h2>Property</h2><ul v-if="Array.isArray(doc.units)"><li v-for="unit in doc.units" :key="unit.name">{{ textValue(unit.unit) }} · {{ textValue(unit.scheme) }}</li></ul><p v-else>Unavailable</p></article>
        <article><h2>External agreement</h2><a v-if="fileLink(doc.signed_copy)" :href="fileLink(doc.signed_copy)" target="_blank" rel="noopener">{{ doc.signed_copy.split('/').pop() }}</a><p v-else>Unavailable</p><p>Signed date: {{ textValue(doc.signed_on) }}</p></article>
      </div>
      <article><h2>Amounts</h2><dl><template v-for="[label, field] in [['Sale price','agreed_price'],['Down payment','down_payment'],['Agreed balance / amount due','amount_due'],['Schedule total','schedule_total']]" :key="field"><dt>{{ label }}</dt><dd>{{ displayMoney(doc[field]) }}</dd></template></dl>
        <p v-if="difference !== null && difference !== 0" role="status">Schedule total {{ displayMoney(doc.schedule_total) }}; agreed amount due {{ displayMoney(doc.amount_due) }}; difference (amount due minus schedule) {{ displayMoney(difference) }}. The server determines whether this blocks registration.</p>
      </article>
      <article><h2>Installment schedule</h2><p>Payment status is unavailable: schedule rows do not record collections.</p><div class="table-scroll"><table><thead><tr><th>Number</th><th>Due date</th><th>Amount</th><th>Status</th></tr></thead><tbody><tr v-for="row in (Array.isArray(doc.schedule) ? doc.schedule : [])" :key="row.name"><td>{{ textValue(row.seq) }}</td><td>{{ textValue(row.due_date) }}</td><td>{{ displayMoney(row.amount) }}</td><td>Unavailable</td></tr></tbody><tfoot><tr><th colspan="2">Total</th><td>{{ displayMoney(doc.schedule_total) }}</td><td>—</td></tr></tfoot></table></div><p v-if="!Array.isArray(doc.schedule)">Schedule unavailable</p><p v-else-if="!doc.schedule.length">No schedule rows recorded.</p></article>
    </template>
    <Teleport defer to="#berjaya-panel"><WorkflowPanel v-if="doc" :timeline="flow" :loading="flowLoading" :error="flowError" @refresh="refreshWorkflow" /></Teleport>
  </section>
</template>
