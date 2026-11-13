<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { LoadingIndicator } from 'frappe-ui'

import { ApiError, apiGet } from '../api'
import StatePanel from '../components/StatePanel.vue'
import WorkflowPanel from '../components/WorkflowPanel.vue'
import { CONTRACT, sourceText, statusText, statusTone, timeline } from '../contracts'
import { dateText, fileLink, isAmount, money, textValue } from '../format'
import { claimPanel, releasePanel } from '../panel'

const route = useRoute()
const doc = ref(null)
const loading = ref(false)
const error = ref(null)
const flow = ref(null)
const flowLoading = ref(false)
const flowError = ref('')
let request = 0
let flowRequest = 0

// A field the server left out of the record (not permitted for this user) is "Unavailable".
const cash = (field, row = doc.value) => (row && field in row ? money(row[field], doc.value?.currency) : 'Unavailable')
const units = computed(() => (Array.isArray(doc.value?.units) ? doc.value.units : null))
const schedule = computed(() => (Array.isArray(doc.value?.schedule) ? doc.value.schedule : null))
const external = computed(() => String(doc.value?.source || '').startsWith('External'))

// Shown for information only: whether a difference blocks registration is the server's call
// and appears in the workflow panel.
const difference = computed(() => {
  const { amount_due: due, schedule_total: total } = doc.value || {}
  if (!isAmount(due) || !isAmount(total)) return null
  const gap = Math.round((Number(due) - Number(total)) * 100) / 100
  return gap === 0 ? null : gap
})

async function refreshWorkflow() {
  if (!doc.value) return
  const id = ++flowRequest
  flowLoading.value = true
  flowError.value = ''
  try {
    const result = await timeline(doc.value.name)
    if (id === flowRequest) flow.value = result
  } catch (err) {
    if (id !== flowRequest) return
    flow.value = null // a failed read leaves no earlier answer on screen
    flowError.value =
      err.kind === 'denied' ? 'You do not have permission to see this workflow.' : err.message || 'The workflow could not be loaded.'
  } finally {
    if (id === flowRequest) flowLoading.value = false
  }
}

async function load() {
  const id = ++request
  ++flowRequest
  doc.value = null
  flow.value = null
  flowError.value = ''
  flowLoading.value = false
  error.value = null
  loading.value = true
  try {
    const result = await apiGet(`${CONTRACT}/${encodeURIComponent(route.params.name)}`)
    if (!result.data?.name) throw new ApiError('server', 'The server sent an unexpected answer.')
    if (id !== request) return
    doc.value = result.data
    refreshWorkflow()
  } catch (err) {
    if (id === request) error.value = err instanceof ApiError ? err : new ApiError('server', 'Something went wrong.')
  } finally {
    if (id === request) loading.value = false
  }
}

function onFocus() {
  if (!flowLoading.value) refreshWorkflow()
}

watch(() => route.params.name, load, { immediate: true })
// The panel belongs to a contract that could be read: no record, no Workflow button.
watch(doc, (now, before) => {
  if (now && !before) claimPanel()
  else if (!now && before) releasePanel()
})
onMounted(() => window.addEventListener('focus', onFocus))
onBeforeUnmount(() => {
  ++request
  ++flowRequest
  window.removeEventListener('focus', onFocus)
  releasePanel()
})
</script>

<template>
  <section class="page">
    <nav class="bj-crumb" aria-label="Breadcrumb">
      <RouterLink class="bj-link" :to="{ name: 'contracts' }">Contracts</RouterLink>
      <span aria-hidden="true">/</span>
      <span>{{ route.params.name }}</span>
    </nav>

    <div v-if="loading" class="page__card bj-loading" role="status"><LoadingIndicator /><span>Loading contract…</span></div>

    <div v-else-if="error" class="page__card">
      <StatePanel
        v-if="error.kind === 'denied'"
        icon="lucide-lock"
        title="This contract is unavailable to you"
        message="Your account does not have permission to read this contract."
      />
      <StatePanel
        v-else
        icon="lucide-triangle-alert"
        tone="blocked"
        title="The contract could not be loaded"
        :message="`${error.message.replace(/[.\s]+$/, '')}. Nothing is shown, because the saved record could not be read.`"
      >
        <button type="button" class="bj-btn bj-btn--primary" @click="load">Try again</button>
      </StatePanel>
    </div>

    <template v-else-if="doc">
      <header class="bj-head">
        <div>
          <h1 class="page__title">{{ doc.name }}</h1>
          <p class="bj-sub">{{ textValue(doc.customer) }}</p>
        </div>
        <div class="bj-toolbar">
          <span v-if="doc.external_reference" class="bj-pill">{{ doc.external_reference }}</span>
          <span class="bj-pill">{{ sourceText(doc) }}</span>
          <span class="bj-pill bj-chip" :class="'bj-chip--' + statusTone(doc.docstatus)">{{ statusText(doc.docstatus) }}</span>
        </div>
      </header>

      <div class="bj-grid">
        <article class="bj-card">
          <h2>Buyer</h2>
          <p class="bj-strong">{{ textValue(doc.customer) }}</p>
          <p class="bj-muted">{{ doc.company || 'Company not recorded' }}</p>
        </article>
        <article class="bj-card">
          <h2>Property</h2>
          <p v-if="!units" class="bj-unavailable">Unavailable</p>
          <p v-else-if="!units.length" class="bj-muted">None recorded</p>
          <template v-else>
            <p v-for="unit in units" :key="unit.name">
              <span class="bj-strong">{{ textValue(unit.unit) }}</span>
              <span v-if="unit.scheme" class="bj-muted"> · {{ unit.scheme }}</span>
            </p>
          </template>
        </article>
        <article class="bj-card">
          <h2>{{ external ? 'External agreement' : 'Signed agreement' }}</h2>
          <p v-if="fileLink(doc.signed_copy)">
            <a class="bj-link" :href="fileLink(doc.signed_copy)" target="_blank" rel="noopener">{{ doc.signed_copy.split('/').pop() }}</a>
          </p>
          <p v-else class="bj-muted">No file attached</p>
          <p class="bj-muted">Signed {{ doc.signed_on ? dateText(doc.signed_on) : 'date not recorded' }}</p>
        </article>
      </div>

      <section class="bj-section">
        <h2>Amounts</h2>
        <div class="page__card bj-card">
          <dl class="bj-kv">
            <div><dt>Sale price</dt><dd>{{ cash('agreed_price') }}</dd></div>
            <div><dt>Down payment</dt><dd>{{ cash('down_payment') }}</dd></div>
            <div><dt>Agreed balance</dt><dd>{{ cash('amount_due') }}</dd></div>
            <div><dt>Schedule total</dt><dd>{{ cash('schedule_total') }}</dd></div>
          </dl>
          <p v-if="difference !== null" class="bj-note" role="status">
            <span class="lucide-info" aria-hidden="true" />
            <span>
              The schedule total is {{ cash('schedule_total') }} and the agreed balance is {{ cash('amount_due') }}: a difference of
              {{ money(difference, doc.currency) }}. Whether this holds up registration is decided by the server and shown in the workflow.
            </span>
          </p>
        </div>
      </section>

      <section class="bj-section">
        <h2>Installment schedule</h2>
        <div class="page__card">
          <StatePanel v-if="!schedule" icon="lucide-eye-off" title="Schedule unavailable" message="Your account may not see this contract's schedule." />
          <StatePanel v-else-if="!schedule.length" icon="lucide-calendar" title="No schedule rows recorded" />
          <template v-else>
            <div class="bj-table-wrap">
              <table class="bj-table bj-table--stack">
                <thead>
                  <tr>
                    <th scope="col">No.</th>
                    <th scope="col">Due date</th>
                    <th scope="col">Type</th>
                    <th scope="col" class="bj-right">Amount</th>
                    <th scope="col">Payment status</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in schedule" :key="row.name">
                    <td data-label="No.">{{ row.seq ?? row.idx ?? '—' }}</td>
                    <td data-label="Due date">{{ dateText(row.due_date) }}</td>
                    <td data-label="Type">{{ row.row_type || 'Installment' }}</td>
                    <td data-label="Amount" class="bj-right">{{ cash('amount', row) }}</td>
                    <td data-label="Payment status"><span class="bj-unavailable">Not recorded</span></td>
                  </tr>
                </tbody>
                <tfoot>
                  <tr>
                    <th scope="row" colspan="3">Total ({{ schedule.length }} {{ schedule.length === 1 ? 'row' : 'rows' }})</th>
                    <td data-label="Total" class="bj-right">{{ cash('schedule_total') }}</td>
                    <td />
                  </tr>
                </tfoot>
              </table>
            </div>
            <p class="bj-foot">Payments against installments are not recorded in the system yet, so no row is shown as paid or unpaid.</p>
          </template>
        </div>
      </section>
    </template>

    <Teleport defer to="#berjaya-panel">
      <WorkflowPanel v-if="doc" :timeline="flow" :loading="flowLoading" :error="flowError" @refresh="refreshWorkflow" />
    </Teleport>
  </section>
</template>
