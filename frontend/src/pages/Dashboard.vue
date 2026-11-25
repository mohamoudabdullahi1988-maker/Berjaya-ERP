<script setup>
import { computed, ref, watch } from 'vue'
import { LoadingIndicator } from 'frappe-ui'

import { ApiError, apiGet } from '../api'
import CompanyPicker from '../components/CompanyPicker.vue'
import DashboardChart from '../components/DashboardChart.vue'
import { numeric } from '../dashboard.js'
import StatePanel from '../components/StatePanel.vue'
import { company } from '../company'
import { dateText, dateTimeText, isAmount, money, percentText, sitePath, textValue } from '../format'
import { RECORDS } from '../records'

// The same server figures as the old /sidra-staff/ dashboard (get_dashboard, decision G21). The
// page adds nothing up: every total is the server's, and a group the user's role cannot read is
// shown with the server's reason, never as zero.
const METHOD = '/api/method/sidra_realestate.api.staff_dashboard.get_dashboard'
const PERIODS = [
  { value: 'this_month', label: 'This month' },
  { value: 'last_30_days', label: 'Last 30 days' },
  { value: 'last_90_days', label: 'Last 90 days' },
]

const period = ref('this_month')
const data = ref(null)
const loading = ref(false)
const error = ref(null)
let request = 0

const cur = computed(() => data.value?.currency)
const periodLabel = computed(() => PERIODS.find((item) => item.value === period.value)?.label.toLowerCase())
const summary = computed(() => data.value?.summary ?? {})
const property = computed(() => data.value?.property ?? null)
const schedule = computed(() => data.value?.schedule ?? null)
const contracts = computed(() => (Array.isArray(data.value?.contracts) ? data.value.contracts : null))
const jobs = computed(() => data.value?.jobs ?? null)
const payments = computed(() => data.value?.payments ?? null)
const sales = computed(() => data.value?.sales ?? null)
const executive = computed(() => (data.value?.executive?.available ? data.value.executive : null))

// A count or amount the server sent as null means "not readable", shown as Unavailable.
const count = (value) => (typeof value === 'number' ? String(value) : 'Unavailable')
const amount = (value) => (isAmount(value) ? money(value, cur.value) : 'Unavailable')

const TILES = computed(() => [
  { label: 'Units available', value: count(summary.value.units_available) },
  { label: 'Active reservations', value: count(summary.value.active_reservations) },
  { label: `Contracts confirmed, ${periodLabel.value}`, value: count(summary.value.confirmed_contracts) },
  {
    label: `Agreed contract value, ${periodLabel.value}`,
    value: amount(summary.value.agreed_contract_value),
    note: 'Commercial value, not revenue',
  },
  { label: `New leads, ${periodLabel.value}`, value: count(summary.value.new_leads) },
])

// Bars are drawn relative to the largest figure in the same list: presentation only.
function bars(items, valueOf) {
  const values = items.map(valueOf).map((v) => (isAmount(v) ? Number(v) : null))
  const top = Math.max(0, ...values.filter((v) => v !== null))
  return items.map((item, i) => ({ item, width: values[i] === null || !top ? 0 : Math.max(2, (values[i] / top) * 100) }))
}

const UNIT_TONE = { Available: 'completed', Reserved: 'current', 'Under Contract': 'current', Sold: 'muted', Blocked: 'blocked' }
const METRICS = [
  ['sales_value', 'Signed sales', 'money'],
  ['available_units', 'Available units', 'count'],
  ['due_next_30_days', 'Due in the next 30 days', 'money'],
  ['overdue_milestones', 'Overdue construction milestones', 'count'],
  ['cash_collected', 'Cash collected', 'money'],
  ['overdue_balance', 'Overdue balance', 'money'],
]
const metric = (key) => executive.value?.metrics?.[key] ?? null
const trend = computed(() => {
  const months = executive.value?.trends?.available ? executive.value.trends.months ?? [] : []
  return { sales: bars(months, (m) => m.sales_value), received: bars(months, (m) => m.received) }
})

const extraTiles = computed(() => [
  { label: 'Open construction jobs', value: jobs.value?.available ? count(jobs.value.open) : 'Unavailable', note: 'Current open jobs' },
  { label: 'Completed construction jobs', value: jobs.value?.available ? count(jobs.value.completed) : 'Unavailable', note: 'Recorded completed jobs' },
  { label: 'Posted receipts', value: payments.value?.available ? amount(payments.value.received) : 'Unavailable', note: payments.value?.notice || payments.value?.reason },
  { label: 'Collection rate', value: payments.value?.available && isAmount(payments.value.collection_rate) ? percentText(payments.value.collection_rate) : 'Unavailable', note: 'Collected of amounts due; supplied by the server' },
])
const dueChart = computed(() => schedule.value?.available ? (schedule.value.buckets || []).map(b => ({ label: b.label, value: numeric(b.amount) ? Number(b.amount) : null })) : [])
const exposureItems = computed(() => executive.value?.exposure?.available ? executive.value.exposure.items || [] : [])
const exposureChart = computed(() => exposureItems.value.filter(item => !item.label.toLowerCase().includes('age')).map(item => ({ label: item.label, value: item.available === true && numeric(item.value) ? Number(item.value) : null })))

async function load() {
  const id = ++request
  data.value = null
  error.value = null
  if (!company.value) return
  loading.value = true
  try {
    const body = await apiGet(METHOD, { company: company.value, period: period.value })
    if (id !== request) return
    if (!body.message || typeof body.message !== 'object') throw new ApiError('server', 'The server sent an unexpected answer.')
    data.value = body.message
  } catch (err) {
    if (id === request) error.value = err instanceof ApiError ? err : new ApiError('server', 'Something went wrong.')
  } finally {
    if (id === request) loading.value = false
  }
}

watch([company, period], load, { immediate: true })
</script>

<template>
  <section class="page">
    <header class="bj-head">
      <div>
        <h1 class="page__title">Dashboard</h1>
        <p class="bj-sub">
          <template v-if="data?.as_of">As at {{ dateTimeText(data.as_of) }}<template v-if="data.scope?.role_label"> · {{ data.scope.role_label }} view</template></template>
          <template v-else>&nbsp;</template>
        </p>
      </div>
      <div class="bj-toolbar">
        <CompanyPicker />
        <label class="bj-label" for="dashboard-period">Period</label>
        <select id="dashboard-period" v-model="period" class="bj-select">
          <option v-for="item in PERIODS" :key="item.value" :value="item.value">{{ item.label }}</option>
        </select>
        <button type="button" class="bj-btn" :disabled="loading" @click="load">Refresh</button>
      </div>
    </header>

    <div v-if="!company" class="page__card">
      <StatePanel icon="lucide-building" title="No Company is available to you" message="The dashboard is shown for one Company at a time, and your account can read none." />
    </div>
    <div v-else-if="loading" class="page__card bj-loading" role="status"><LoadingIndicator /><span>Loading the dashboard…</span></div>
    <div v-else-if="error" class="page__card">
      <StatePanel
        :icon="error.kind === 'denied' ? 'lucide-lock' : 'lucide-triangle-alert'"
        :tone="error.kind === 'denied' ? 'muted' : 'blocked'"
        :title="error.kind === 'denied' ? 'The dashboard is unavailable to you' : 'The dashboard could not be loaded'"
        :message="`${error.message.replace(/[.\s]+$/, '')}. No figure is shown.`"
      >
        <button type="button" class="bj-btn bj-btn--primary" @click="load">Try again</button>
      </StatePanel>
    </div>

    <template v-else-if="data">
      <div class="bj-grid tiles">
        <article v-for="tile in TILES" :key="tile.label" class="bj-card">
          <h2>{{ tile.label }}</h2>
          <p class="bj-figure" :class="{ 'bj-unavailable': tile.value === 'Unavailable' }">{{ tile.value }}</p>
          <p v-if="tile.note" class="bj-muted small">{{ tile.note }}</p>
        </article>
      </div>

      <section class="bj-section" aria-label="Operational summary">
        <h2>Operations at a glance</h2>
        <div class="bj-grid"><article v-for="tile in extraTiles" :key="tile.label" class="bj-card"><h2>{{ tile.label }}</h2><p class="bj-figure" :class="{ 'bj-unavailable': tile.value === 'Unavailable' }">{{ tile.value }}</p><p class="bj-muted small">{{ tile.note }}</p></article></div>
      </section>
      <div class="two additional-charts">
        <DashboardChart title="Scheduled amounts by due window" :rows="dueChart" :currency="cur" note="Contractual schedule before settlement; these amounts are not expected cash receipts." />
        <DashboardChart title="Operational exceptions" :rows="exposureChart" kind="count" tone="blue" :note="executive ? 'Current saved exceptions, not approved project baseline performance.' : 'Management reporting unavailable to this role.'" />
      </div>
      <section v-if="exposureItems.length" class="bj-section"><h2>Risk and exposure</h2><div class="bj-grid"><article v-for="item in exposureItems" :key="item.label" class="bj-card"><h2>{{ item.label }}</h2><p class="bj-figure">{{ item.available === true ? count(item.value) : 'Unavailable' }}</p><p class="bj-muted small">{{ item.available ? item.detail : item.reason }}</p><a v-if="item.available && sitePath(item.drilldown?.path)" class="bj-link small" :href="sitePath(item.drilldown.path)">View supporting records</a></article></div></section>
      <section v-if="executive?.decisions?.available" class="bj-section"><h2>Needs attention</h2><p class="bj-muted small">{{ executive.decisions.summary }}</p><div class="bj-grid"><article v-for="item in executive.decisions.items" :key="item.id" class="bj-card"><h2>{{ item.title }}</h2><p>{{ item.reference }}</p><p class="bj-muted small">{{ item.owner || 'Owner not assigned' }} · {{ dateText(item.due_date) }}</p><p>{{ item.next_action }}</p><a v-if="sitePath(item.drilldown?.path)" class="bj-link small" :href="sitePath(item.drilldown.path)">Review record</a></article></div><p v-if="!executive.decisions.items?.length" class="bj-muted">No recorded exceptions in this scope.</p></section>

      <!-- Management figures: only for roles the server gives executive reporting to. -->
      <section v-if="executive" class="bj-section">
        <h2>Management</h2>
        <p v-if="executive.period_label" class="bj-muted small">{{ executive.period_label }}</p>
        <div class="bj-grid">
          <article v-for="[key, label, kind] in METRICS" :key="key" class="bj-card">
            <h2>{{ label }}</h2>
            <template v-if="metric(key)?.available">
              <p class="bj-figure">{{ kind === 'money' ? amount(metric(key).value) : count(metric(key).value) }}</p>
              <p v-if="metric(key).detail" class="bj-muted small">{{ metric(key).detail }}</p>
              <p v-if="sitePath(metric(key).drilldown?.path)"><a class="bj-link small" :href="sitePath(metric(key).drilldown.path)">Open the records</a></p>
            </template>
            <template v-else>
              <p class="bj-figure bj-unavailable">Unavailable</p>
              <p class="bj-muted small">{{ metric(key)?.reason || 'Not provided by the server.' }}</p>
            </template>
          </article>
        </div>
        <div v-if="trend.sales.length" class="page__card bj-card trend">
          <h2>Last six months</h2>
          <p class="bj-muted small">{{ executive.trends.period_label }}</p>
          <div class="trend__rows">
            <div v-for="({ item, width }, i) in trend.sales" :key="item.label" class="trend__row">
              <span class="trend__label">{{ item.label }}</span>
              <span class="trend__bars">
                <span class="bar"><i class="bar__fill" :style="{ width: width + '%' }" /><span class="bar__text">Sales {{ amount(item.sales_value) }}</span></span>
                <span class="bar"><i class="bar__fill bar__fill--alt" :style="{ width: trend.received[i].width + '%' }" /><span class="bar__text">Received {{ amount(item.received) }}</span></span>
              </span>
            </div>
          </div>
        </div>
      </section>

      <div class="two">
        <section class="bj-section">
          <h2>Properties by status</h2>
          <div class="page__card bj-card">
            <p v-if="!property || property.total === null" class="bj-unavailable">Unavailable to your role</p>
            <p v-else-if="!property.total" class="bj-muted">No units on record.</p>
            <template v-else>
              <p class="bj-muted small">{{ property.total }} units</p>
              <div v-for="{ item, width } in bars(property.counts, (c) => c.count)" :key="item.status" class="meter">
                <span class="bj-chip" :class="'bj-chip--' + (UNIT_TONE[item.status] || 'muted')">{{ item.status }}</span>
                <span class="meter__track"><i :style="{ width: width + '%' }" /></span>
                <strong>{{ item.count }}</strong>
              </div>
              <p><RouterLink class="bj-link small" :to="{ name: 'properties' }">Open Properties</RouterLink></p>
            </template>
          </div>
        </section>

        <section class="bj-section">
          <h2>Installments falling due</h2>
          <div class="page__card bj-card">
            <p v-if="!schedule?.available" class="bj-unavailable">{{ schedule?.reason || 'Unavailable to your role' }}</p>
            <p v-else-if="!schedule.buckets.length" class="bj-muted">Nothing scheduled from confirmed contracts.</p>
            <template v-else>
              <dl class="bj-kv">
                <div v-for="bucket in schedule.buckets" :key="bucket.label"><dt>{{ bucket.label }}</dt><dd>{{ amount(bucket.amount) }}</dd></div>
              </dl>
              <p class="bj-muted small">Agreed schedule, not receipts: payments against installments are not recorded yet.</p>
              <p><RouterLink class="bj-link small" :to="{ name: 'collections' }">Open Collections</RouterLink></p>
            </template>
          </div>
        </section>
      </div>

      <section v-if="contracts" class="bj-section">
        <h2>Latest contracts</h2>
        <div class="page__card">
          <p v-if="!contracts.length" class="bj-foot">No contracts for this Company yet.</p>
          <div v-else class="bj-table-wrap">
            <table class="bj-table bj-table--stack">
              <thead>
                <tr>
                  <th scope="col">Contract</th>
                  <th scope="col">Customer</th>
                  <th scope="col">Property</th>
                  <th scope="col">Signed</th>
                  <th scope="col" class="bj-right">Value</th>
                  <th scope="col">Status</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in contracts.slice(0, 8)" :key="row.id">
                  <td data-label="Contract">
                    <span>
                      <RouterLink class="bj-link" :to="{ name: RECORDS.contracts.detailRoute, params: { name: row.id } }">{{ row.id }}</RouterLink>
                      <span v-if="row.reference && row.reference !== row.id" class="bj-small">{{ row.reference }}</span>
                    </span>
                  </td>
                  <td data-label="Customer">{{ textValue(row.customer_display) }}</td>
                  <td data-label="Property">{{ row.unit_label || '—' }}</td>
                  <td data-label="Signed">{{ dateText(row.signed_on) }}</td>
                  <td data-label="Value" class="bj-right">{{ isAmount(row.value) ? money(row.value, row.currency) : 'Unavailable' }}</td>
                  <td data-label="Status"><span class="bj-chip" :class="row.status === 'Confirmed' ? 'bj-chip--completed' : 'bj-chip--current'">{{ row.status }}</span></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <div class="two">
        <section class="bj-section">
          <h2>Construction</h2>
          <div class="page__card bj-card">
            <p v-if="!jobs?.available" class="bj-unavailable">{{ jobs?.reason || 'Unavailable to your role' }}</p>
            <template v-else>
              <dl class="bj-kv">
                <div><dt>Open jobs</dt><dd>{{ count(jobs.open) }}</dd></div>
                <div><dt>Contracted or in progress</dt><dd>{{ count(jobs.active) }}</dd></div>
                <div><dt>Overdue milestones</dt><dd>{{ count(jobs.overdue_milestones) }}</dd></div>
                <div><dt>Completed</dt><dd>{{ count(jobs.completed) }}</dd></div>
              </dl>
              <ul class="jobs">
                <li v-for="job in (jobs.items ?? []).slice(0, 5)" :key="job.id">
                  <RouterLink class="bj-link" :to="{ name: RECORDS.jobs.detailRoute, params: { name: job.id } }">{{ job.label }}</RouterLink>
                  <span class="bj-muted"> · {{ job.status }}<template v-if="job.next_milestone"> · next: {{ job.next_milestone }}<template v-if="job.due_date"> by {{ dateText(job.due_date) }}</template></template></span>
                </li>
              </ul>
              <p><RouterLink class="bj-link small" :to="{ name: 'construction' }">Open Construction</RouterLink></p>
            </template>
          </div>
        </section>

        <section class="bj-section">
          <h2>Payments</h2>
          <div class="page__card bj-card">
            <template v-if="payments?.available">
              <dl class="bj-kv">
                <div><dt>Received, {{ periodLabel }}</dt><dd>{{ amount(payments.received) }}</dd></div>
                <div><dt>Overdue</dt><dd>{{ amount(payments.overdue) }}</dd></div>
                <div><dt>Collected of amounts due</dt><dd>{{ percentText(payments.collection_rate) }}</dd></div>
              </dl>
              <p v-if="payments.notice" class="bj-muted small">{{ payments.notice }}</p>
              <p><RouterLink class="bj-link small" :to="{ name: 'finance' }">Open Finance</RouterLink></p>
            </template>
            <p v-else class="bj-unavailable">{{ payments?.reason || 'Unavailable to your role' }}</p>
          </div>
        </section>
      </div>

      <section class="bj-section">
        <h2>Sales activity, {{ periodLabel }}</h2>
        <div class="page__card bj-card">
          <template v-if="sales?.available">
            <p v-if="!sales.pipeline?.length" class="bj-muted">No leads recorded in this period.</p>
            <div v-for="{ item, width } in bars(sales.pipeline ?? [], (p) => p.value)" :key="item.label" class="meter">
              <span class="meter__name">{{ item.label }}</span>
              <span class="meter__track"><i :style="{ width: width + '%' }" /></span>
              <strong>{{ item.value }}</strong>
            </div>
            <p v-if="sales.notice" class="bj-muted small">{{ sales.notice }}</p>
          </template>
          <p v-else class="bj-unavailable">{{ sales?.reason || 'Unavailable to your role' }}</p>
        </div>
      </section>
    </template>
  </section>
</template>

<style scoped>
.small {
  font-size: 13px;
}
.tiles {
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
}
.two {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 0 16px;
}
.two > .bj-section > .bj-card,
.bj-section > .bj-card {
  margin-top: 8px;
}
.meter {
  display: grid;
  grid-template-columns: minmax(110px, auto) 1fr auto;
  align-items: center;
  gap: 12px;
  padding: 6px 0;
  font-size: 14px;
}
.meter__name {
  color: var(--bj-ink);
}
.meter__track {
  height: 8px;
  background: var(--bj-ground);
  border-radius: 4px;
  overflow: hidden;
}
.meter__track i {
  display: block;
  height: 100%;
  background: var(--bj-terracotta-light);
}
.jobs {
  margin: 12px 0 4px;
  padding: 0;
  list-style: none;
  font-size: 14px;
}
.jobs li {
  padding: 4px 0;
}
.trend {
  margin-top: 16px;
}
.trend__rows {
  display: grid;
  gap: 10px;
  margin-top: 8px;
}
.trend__row {
  display: grid;
  grid-template-columns: 80px 1fr;
  gap: 12px;
  align-items: center;
  font-size: 13px;
}
.trend__bars {
  display: grid;
  gap: 4px;
}
.bar {
  position: relative;
  display: block;
  height: 22px;
  background: var(--bj-ground);
  border-radius: 4px;
  overflow: hidden;
}
.bar__fill {
  position: absolute;
  inset: 0 auto 0 0;
  background: var(--bj-terracotta-light);
}
.bar__fill--alt {
  background: var(--bj-charcoal);
  opacity: 0.25;
}
.bar__text {
  position: relative;
  padding: 0 8px;
  line-height: 22px;
  color: var(--bj-ink);
  white-space: nowrap;
}
</style>

<style scoped>.additional-charts { margin: 24px 0; }</style>
