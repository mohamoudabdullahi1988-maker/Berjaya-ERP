<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { LoadingIndicator } from 'frappe-ui'

import KpiTile from '../showcase/components/KpiTile.vue'
import DonutCard from '../showcase/components/DonutCard.vue'
import BarsCard from '../showcase/components/BarsCard.vue'
import HBarsCard from '../showcase/components/HBarsCard.vue'
import GanttCard from '../showcase/components/GanttCard.vue'
import MapCard from '../showcase/components/MapCard.vue'
import TableCard from '../showcase/components/TableCard.vue'
import ListCard from '../showcase/components/ListCard.vue'
import { MODULES } from '../showcase/modules'
import { recordAction } from '../showcase/link'
import { ApiError, apiGet } from '../api'
import { company } from '../company'
import StatePanel from '../components/StatePanel.vue'
import CompanyPicker from '../components/CompanyPicker.vue'
import PeriodPicker from '../components/PeriodPicker.vue'
import { periodFrom, periodLabel } from '../showcase/period'
import { executivePage, LIVE_METHOD, LIVE_TABS, REALESTATE_METHOD, liveMethod, livePageFor } from '../showcase/live'
import { loadExecutiveSources, validLiveSource } from '../showcase/liveSources'

const WIDGETS = { donut: DonutCard, bars: BarsCard, hbars: HBarsCard, gantt: GanttCard, map: MapCard, table: TableCard, list: ListCard }

const route = useRoute()
const module = computed(() => MODULES[route.meta.showcase])
const tabKeys = computed(() => Object.keys(module.value.tabs))
const tab = computed(() => (tabKeys.value.includes(route.params.tab) ? route.params.tab : tabKeys.value[0]))
const pageMeta = computed(() => module.value.tabs[tab.value])
const hasLiveReport = computed(() => (LIVE_TABS[route.meta.showcase] ?? []).includes(tab.value))
const period = computed(() => periodFrom(route.query))
const periodKey = computed(() => `${period.value.from}|${period.value.to}`)
const liveData = ref(null)
const liveError = ref(null)
const loading = ref(false)
let request = 0
async function loadLive() {
  const id = ++request
  liveData.value = null
  liveError.value = null
  loading.value = false
  if (!hasLiveReport.value) return
  if (!company.value) {
    liveError.value = 'No Company is available to your account.'
    return
  }
  loading.value = true
  try {
    const selectedCompany = company.value
    if (route.meta.showcase === 'executive') {
      const result = await loadExecutiveSources(selectedCompany, apiGet, period.value)
      if (id === request) liveData.value = result
      return
    }
    const method = liveMethod(route.meta.showcase, tab.value)
    const kind = method === LIVE_METHOD ? 'construction' : method === REALESTATE_METHOD ? 'realestate' : method.endsWith('get_operations_live') ? 'operations' : method.endsWith('get_crm_live') ? 'crm' : 'finance'
    const body = await apiGet(method, { company: selectedCompany, from_date: period.value.from, to_date: period.value.to })
    if (id !== request) return
    if (!validLiveSource(body?.message, selectedCompany, kind)) throw new ApiError('server', 'The server sent incompatible records or another Company.')
    liveData.value = body.message
  } catch (error) {
    if (id !== request) return
    liveData.value = null
    liveError.value = error instanceof ApiError ? error.message : 'The live records could not be loaded.'
  } finally {
    if (id === request) loading.value = false
  }
}
watch([hasLiveReport, () => company.value, () => route.meta.showcase, tab, periodKey], loadLive, { immediate: true })

const periodNote = computed(() => {
  const executive = route.meta.showcase === 'executive' && !['month', '3m'].includes(period.value.key)
  return executive ? 'Executive totals from the dashboard cover the last 90 days at most; construction and sales below follow the period.' : `Live records for ${periodLabel(period.value)}. Figures marked as of today (units, stock, open risks, amounts owed) do not change with the period.`
})
const page = computed(() => {
  if (!liveData.value) return null
  if (route.meta.showcase === 'executive') return executivePage(liveData.value, pageMeta.value)
  return livePageFor(route.meta.showcase, tab.value, liveData.value, pageMeta.value)
})
const records = computed(() => (module.value.records ?? []).map(recordAction).filter(Boolean))

onBeforeUnmount(() => { ++request })
</script>

<template>
  <div class="page sc" :class="{ 'sc--live-executive': route.meta.showcase === 'executive' }">
    <header class="sc__head">
      <div class="sc__titles">
        <p class="sc__module">{{ module.label }}</p>
        <h1 class="page__title">{{ pageMeta.title }}</h1>
        <p v-if="page" class="sc__subtitle">{{ page.subtitle }}</p>
      </div>
      <nav v-if="records.length" class="sc__records" aria-label="Real records">
        <RouterLink v-for="r in records" :key="r.label" :to="r.to" class="sc__record">{{ r.label }}<span class="lucide-arrow-up-right" aria-hidden="true" /></RouterLink>
      </nav>
    </header>

    <nav v-if="tabKeys.length > 1" class="sc__tabs" aria-label="Screens in this module">
      <RouterLink
        v-for="key in tabKeys"
        :key="key"
        :to="{ name: module.route, params: { tab: key }, query: { period: route.query.period, from: route.query.from, to: route.query.to } }"
        class="sc__tab"
        :class="{ 'sc__tab--on': key === tab }"
        :aria-current="key === tab ? 'page' : undefined"
      >{{ module.tabLabels[key] }}</RouterLink>
    </nav>

    <div v-if="hasLiveReport" class="bj-toolbar sc__filters">
      <CompanyPicker />
      <button type="button" class="bj-btn" :disabled="loading || !company" @click="loadLive">Refresh</button>
    </div>

    <PeriodPicker v-if="hasLiveReport && company" :note="periodNote" />

    <p v-if="loading" class="sc__state" role="status"><LoadingIndicator class="h-4 w-4" />Loading live records…</p>
    <StatePanel v-else-if="liveError" icon="lucide-triangle-alert" tone="blocked" title="Live records could not be loaded" :message="liveError" />
    <StatePanel v-else-if="!hasLiveReport" icon="lucide-chart-no-axes-combined" title="Live report unavailable" />

    <section v-if="page?.kpis.length" class="sc__kpis" :style="{ '--n': page.kpis.length }" aria-label="Key figures">
      <KpiTile v-for="tile in page.kpis" :key="tile.label" :tile="tile" />
    </section>

    <section v-if="page?.widgets.length" class="sc__grid">
      <div v-for="(widget, i) in page.widgets" :key="tab + i" class="sc__cell" :class="{ 'sc__cell--full': widget.span === 12 }" :style="{ '--span': widget.span ?? 6 }">
        <component :is="WIDGETS[widget.type]" :widget="widget" />
      </div>
    </section>

  </div>
</template>

<style scoped>
.sc { max-width: 1440px; }
.sc__head { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: flex-end; gap: 12px 20px; margin-bottom: 14px; }
.sc__module { margin: 0 0 2px; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; color: var(--bj-terracotta); }
.page__title { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; font-size: 24px; }
.sc__subtitle { margin: 4px 0 0; font-size: 14px; color: var(--bj-muted); }
.sc__filters { margin-bottom: 12px; }
.sc__state { display: flex; align-items: center; gap: 8px; color: var(--bj-muted); font-size: 14px; }
.sc__records { display: flex; flex-wrap: wrap; gap: 8px; }
.sc__record { display: inline-flex; align-items: center; gap: 6px; min-height: 36px; padding: 6px 12px; border: 1px solid var(--bj-line); border-radius: 8px; background: var(--bj-card); font-size: 13px; font-weight: 500; color: var(--bj-ink); text-decoration: none; }
.sc__record:hover { border-color: var(--bj-terracotta); color: var(--bj-terracotta); }
.sc__record span { width: 14px; height: 14px; color: var(--bj-muted); }
.sc__tabs { display: flex; gap: 4px; margin: 0 0 16px; overflow-x: auto; border-bottom: 1px solid var(--bj-line); scrollbar-width: thin; }
.sc__tab { display: inline-flex; align-items: center; min-height: 42px; padding: 8px 14px; font-size: 14px; font-weight: 500; color: var(--bj-muted); white-space: nowrap; text-decoration: none; border-bottom: 2px solid transparent; }
.sc__tab:hover { color: var(--bj-ink); }
.sc__tab--on { color: var(--bj-terracotta); border-bottom-color: var(--bj-terracotta); }
.sc__kpis { display: grid; grid-template-columns: repeat(var(--n), minmax(0, 1fr)); gap: 12px; margin-bottom: 14px; }
.sc__grid { display: grid; grid-template-columns: repeat(12, minmax(0, 1fr)); gap: 14px; }
.sc__cell { grid-column: span var(--span); min-width: 0; }
@media (max-width: 1280px) {
  .sc__kpis { grid-template-columns: repeat(min(var(--n), 3), minmax(0, 1fr)); }
  .sc__cell { grid-column: span max(6, var(--span)); }
}
@media (max-width: 900px) {
  .sc__cell { grid-column: span 12; }
}
@media (max-width: 640px) {
  .sc__kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
  .page__title { font-size: 20px; }
}
</style>

<style scoped>
.sc--live-executive .sc__kpis { grid-template-columns: repeat(4, minmax(0, 1fr)); }
.sc--live-executive .sc__grid { grid-auto-flow: row dense; align-items: stretch; }
@media (min-width: 901px) and (max-width: 1280px) {
  .sc--live-executive .sc__cell { grid-column: span 6; }
  .sc--live-executive .sc__cell--full { grid-column: span 12; }
}
@media (max-width: 640px) {
  .sc--live-executive .sc__kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>
