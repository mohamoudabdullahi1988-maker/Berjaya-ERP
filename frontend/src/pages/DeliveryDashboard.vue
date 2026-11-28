<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import { apiGet } from '../api'
import { boot, canOpen, canRead } from '../boot'
import AgreementAccounting from '../components/AgreementAccounting.vue'
import CompanyPicker from '../components/CompanyPicker.vue'
import NativeReports from '../components/NativeReports.vue'
import { company } from '../company'
import { dateText, deskLink, money } from '../format'

const ENDPOINT = '/api/method/sidra_realestate.api.delivery_dashboard.'
const reports = [
  { key: 'statement', label: 'Customer statement by contract', detail: 'Agreed amounts and payment schedule', icon: 'lucide-file-text' },
  { key: 'overdue', label: 'Overdue installments', detail: 'Unpaid payment terms on posted invoices', icon: 'lucide-calendar' },
  { key: 'suppliers', label: 'Supplier balances and payments', detail: 'Accounts payable and posted supplier payments', icon: 'lucide-landmark' },
]
const route = useRoute()
const view = computed(() => route.query.view)
const report = computed(() => reports.find(({ key }) => key === view.value))
const isLookup = computed(() => ['statement', 'payment'].includes(view.value))
const lookup = ref('')
const matches = ref(null)
const result = ref(null)
const error = ref('')
const busy = ref(false)
const today = new Date()
const dateInput = (date) => [date.getFullYear(), date.getMonth() + 1, date.getDate()]
  .map((part) => String(part).padStart(2, '0')).join('-')
const fromDate = ref(dateInput(new Date(today.getFullYear(), today.getMonth(), 1)))
const toDate = ref(dateInput(today))
let generation = 0

function reset() {
  generation += 1
  matches.value = null
  result.value = null
  error.value = ''
  busy.value = false
}

async function request(method, options = {}, append = false) {
  const id = ++generation
  const previous = append ? result.value : null
  busy.value = true
  error.value = ''
  if (!append) result.value = null
  if (method === 'find_agreements') matches.value = null
  try {
    const { message } = await apiGet(ENDPOINT + method, {
      company: company.value,
      ...options,
      start: previous?.next_start,
    })
    if (id !== generation) return
    if (method === 'find_agreements') matches.value = message
    else if (previous) result.value = { ...message, rows: [...previous.rows, ...message.rows] }
    else result.value = message
  } catch (err) {
    if (id === generation) error.value = err.message
  } finally {
    if (id === generation) busy.value = false
  }
}

function loadReport(append = false) {
  if (view.value === 'overdue') return request('overdue_installments', {}, append)
  if (view.value === 'suppliers') {
    return request('supplier_payments', { from_date: fromDate.value, to_date: toDate.value }, append)
  }
  if (view.value === 'statement' && typeof route.query.contract === 'string') {
    return request('contract_statement', {
      contract: route.query.contract,
      agreement_type: route.query.agreement_type,
    })
  }
}

function paymentLink(customer) {
  const filters = new URLSearchParams({ company: company.value, party_type: 'Customer', party: customer })
  return '/desk/payment-entry?' + filters
}

watch([company, view], () => {
  lookup.value = ''
  reset()
  if (company.value) loadReport()
}, { immediate: true })

watch(() => [route.query.contract, route.query.agreement_type], () => {
  if (company.value && view.value === 'statement') loadReport()
})
</script>

<template>
  <section class="page">
    <header class="bj-head">
      <h1 class="page__title">Berjaya Dashboard</h1>
      <div class="bj-toolbar">
        <CompanyPicker />
        <a v-if="boot.can_open_projects" class="bj-btn" href="/desk/project">Construction projects</a>
      </div>
    </header>

    <h2 class="section-title">Reports</h2>
    <div class="delivery-grid">
      <RouterLink
        v-for="item in reports" :key="item.key" class="bj-card tile"
        :to="{ name: 'delivery', query: { view: item.key } }"
        :aria-current="view === item.key ? 'page' : undefined"
      >
        <span class="tile-icon" :class="item.icon" aria-hidden="true" />
        <strong>{{ item.label }}</strong>
        <span class="bj-muted">{{ item.detail }}</span>
      </RouterLink>
    </div>

    <h2 class="section-title">Transactions</h2>
    <div class="bj-toolbar shortcuts">
      <RouterLink v-if="canRead('contracts') || canRead('jobs')" class="bj-btn" :to="{ name: 'delivery', query: { view: 'payment' } }">Find an agreement for payment</RouterLink>
      <RouterLink v-if="canOpen('cashbook')" class="bj-btn" :to="{ name: 'cashbook' }">Cashbook &amp; Reconciliation</RouterLink>
      <RouterLink v-if="canRead('reservations')" class="bj-btn" :to="{ name: 'reservations-list' }">Plot reservations</RouterLink>
      <RouterLink v-if="canRead('sale_quotations')" class="bj-btn" :to="{ name: 'sale_quotations-list' }">Sale quotations</RouterLink>
    </div>

    <section v-if="report || isLookup" class="bj-card detail" aria-labelledby="delivery-detail">
      <h2 id="delivery-detail" class="section-title">{{ report?.label || 'Find an agreement for payment' }}</h2>
      <p v-if="!company" class="bj-muted">No company is available to your account.</p>
      <template v-else>
        <template v-if="isLookup">
          <form class="bj-toolbar report-form" @submit.prevent="request('find_agreements', { text: lookup })">
            <label for="agreement-search">Customer name or phone, plot or agreement reference</label>
            <input id="agreement-search" v-model.trim="lookup" class="bj-input" type="search" minlength="2" maxlength="100" required @input="reset" />
            <button class="bj-btn" :disabled="busy">Find agreements</button>
          </form>
          <p v-if="matches && !matches.contracts.length && !matches.jobs.length" role="status">No matching agreements you can access.</p>
          <ul v-if="matches" class="matches">
            <li v-for="row in matches.contracts" :key="row.name">
              <div>
                <RouterLink class="bj-link" :to="{ name: 'contract-detail', params: { name: row.name } }">{{ row.external_reference || row.name }}</RouterLink>
                <span class="bj-small">{{ row.customer }}</span>
              </div>
              <div class="bj-toolbar">
                <RouterLink class="bj-btn" :to="{ name: 'delivery', query: { view: 'statement', contract: row.name } }">View statement</RouterLink>
                <a v-if="view === 'payment' && matches.can_open_payments && row.customer" class="bj-btn" :href="paymentLink(row.customer)">Open payment entries</a>
              </div>
            </li>
            <li v-for="row in matches.jobs" :key="row.name">
                <div>
                  <RouterLink class="bj-link" :to="{ name: 'construction-detail', params: { name: row.name } }">{{ row.name }}</RouterLink>
                  <span class="bj-small">{{ row.customer }}</span>
                </div>
                <div class="bj-toolbar">
                  <RouterLink class="bj-btn" :to="{ name: 'delivery', query: { view: 'statement', contract: row.name, agreement_type: 'construction' } }">View statement</RouterLink>
                  <a v-if="view === 'payment' && matches.can_open_payments && row.customer" class="bj-btn" :href="paymentLink(row.customer)">Open payment entries</a>
                </div>
            </li>
          </ul>
          <p v-if="view === 'payment'" class="bj-muted">In ERPNext, verify the invoice against the selected agreement before recording or allocating a payment.</p>
        </template>

        <template v-if="view === 'statement' && result">
          <h3>{{ result.contract }}</h3>
          <p>{{ result.customer }}<span v-if="result.signed_on"> · Signed {{ dateText(result.signed_on) }}</span></p>
          <p>
            {{ result.agreement_type === 'construction' ? 'Current contract value' : 'Agreed price' }}
            <strong>{{ money(result.agreed_price, result.currency) }}</strong>
            <span v-if="result.schedule_total != null"> · Scheduled total <strong>{{ money(result.schedule_total, result.currency) }}</strong></span>
          </p>
          <div v-if="result.schedule.length" class="bj-table-wrap">
            <table class="bj-table">
              <thead><tr><th scope="col">Due date</th><th scope="col">Type</th><th scope="col" class="bj-right">Scheduled amount</th></tr></thead>
              <tbody><tr v-for="(row, index) in result.schedule" :key="index"><td>{{ dateText(row.due_date) }}</td><td>{{ row.type }}</td><td class="bj-right">{{ money(row.amount, result.currency) }}</td></tr></tbody>
            </table>
          </div>
          <p v-else-if="result.agreement_type !== 'construction'">No installment schedule is recorded for this contract.</p>
          <AgreementAccounting v-if="result.accounting" :company="company" :statement="result" @verified="loadReport()" />
        </template>

        <template v-if="view === 'overdue'">
          <p class="bj-muted">From ERPNext Accounts Receivable by payment terms. Unlinked Sidra contract schedules are outside this report.</p>
          <p v-if="result" class="bj-muted">As of {{ dateText(result.as_of) }}</p>
          <div v-if="result?.rows.length" class="bj-table-wrap">
            <table class="bj-table">
              <thead><tr><th scope="col">Invoice</th><th scope="col">Agreement</th><th scope="col">Customer</th><th scope="col">Term</th><th scope="col">Due date</th><th scope="col" class="bj-right">Outstanding</th></tr></thead>
              <tbody><tr v-for="(row, index) in result.rows" :key="index">
                <td><a class="bj-link" :href="deskLink('Sales Invoice', row.invoice)">{{ row.invoice }}</a></td>
                <td>
                  <RouterLink v-if="row.agreement" class="bj-link" :to="{ name: 'delivery', query: { view: 'statement', contract: row.agreement.name, agreement_type: row.agreement.type } }">{{ row.agreement.name }}</RouterLink>
                  <span v-else>—</span>
                </td>
                <td>{{ row.customer }}</td><td>{{ row.term || '—' }}</td><td>{{ dateText(row.due_date) }}</td><td class="bj-right">{{ money(row.outstanding, result.currency) }}</td>
              </tr></tbody>
            </table>
          </div>
          <p v-else-if="result">No overdue invoice payment terms found.</p>
        </template>

        <template v-if="view === 'suppliers'">
          <NativeReports :key="company" preset="Accounts Payable" />
          <h3>Posted supplier payments</h3>
          <form class="bj-toolbar report-form" @submit.prevent="loadReport()">
            <label>From <input v-model="fromDate" type="date" class="bj-input" required @input="reset" /></label>
            <label>To <input v-model="toDate" type="date" class="bj-input" required @input="reset" /></label>
            <button class="bj-btn" :disabled="busy">Show payments</button>
          </form>
          <div v-if="result?.rows.length" class="bj-table-wrap">
            <table class="bj-table">
              <thead><tr><th scope="col">Payment</th><th scope="col">Supplier</th><th scope="col">Posted</th><th scope="col" class="bj-right">Amount from paying account</th></tr></thead>
              <tbody><tr v-for="row in result.rows" :key="row.name">
                <td><a class="bj-link" :href="deskLink('Payment Entry', row.name)">{{ row.name }}</a></td>
                <td>{{ row.party }}</td><td>{{ dateText(row.posting_date) }}</td><td class="bj-right">{{ money(row.paid_amount, row.paid_from_account_currency) }}</td>
              </tr></tbody>
            </table>
          </div>
          <p v-else-if="result">No submitted supplier payments in this period.</p>
        </template>
        <button v-if="result?.has_more" class="bj-btn more" :disabled="busy" @click="loadReport(true)">Load more</button>
        <p v-if="busy" role="status">Loading…</p>
        <p v-if="error" role="alert">{{ error }}</p>
      </template>
    </section>
  </section>
</template>

<style scoped>
.section-title { font-size: 17px; font-weight: 650; margin: 0 0 12px; }
.delivery-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 215px), 1fr)); gap: 14px; margin-bottom: 24px; }
.tile { display: grid; gap: 8px; text-decoration: none; color: inherit; }
.tile:hover, .tile[aria-current="page"] { border-color: var(--bj-accent); }
.tile-icon { width: 20px; height: 20px; color: var(--bj-accent); }
.shortcuts { margin-bottom: 24px; }
.detail p, .detail h3 { margin: 12px 0; }
.detail h3 { font-weight: 650; }
.report-form { align-items: end; margin-bottom: 12px; }
.report-form label { display: grid; gap: 6px; }
.report-form label[for] { flex-basis: 100%; }
.report-form input[type="search"] { min-width: min(100%, 310px); }
.matches { list-style: none; padding: 0; }
.matches li { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; border-bottom: 1px solid var(--bj-line); padding: 10px 0; }
.more { margin-top: 12px; }
</style>
