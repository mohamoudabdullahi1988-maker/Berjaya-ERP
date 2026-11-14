<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { LoadingIndicator } from 'frappe-ui'

import { ApiError, apiGet } from '../api'
import { canRead } from '../boot'
import { currencyOf } from '../company'
import FieldValue from '../components/FieldValue.vue'
import RelatedList from '../components/RelatedList.vue'
import StatePanel from '../components/StatePanel.vue'
import { deskLink } from '../format'
import { RECORDS, listRoute } from '../records'

// One saved record, read-only, laid out as described in records.js. Editing is in Desk.
const route = useRoute()
const key = route.meta.list
const config = RECORDS[key]
const detail = config.detail

const doc = ref(null)
const loading = ref(false)
const error = ref(null)
let request = 0

const currency = computed(() => doc.value?.currency || currencyOf(doc.value?.company))
const title = computed(() => (detail.title && doc.value?.[detail.title]) || doc.value?.name)
const desk = computed(() => deskLink(config.doctype, doc.value?.name))
const related = computed(() => (detail.related ?? []).filter((item) => canRead(item.list)))
const right = (column) => ['money', 'int', 'number', 'percent'].includes(column.type)

async function load() {
  const id = ++request
  doc.value = null
  error.value = null
  loading.value = true
  try {
    const result = await apiGet(`/api/resource/${encodeURIComponent(config.doctype)}/${encodeURIComponent(route.params.name)}`)
    if (!result.data?.name) throw new ApiError('server', 'The server sent an unexpected answer.')
    if (id === request) doc.value = result.data
  } catch (err) {
    if (id === request) error.value = err instanceof ApiError ? err : new ApiError('server', 'Something went wrong.')
  } finally {
    if (id === request) loading.value = false
  }
}

watch(() => route.params.name, load, { immediate: true })
onBeforeUnmount(() => ++request)
</script>

<template>
  <section class="page">
    <nav class="bj-crumb" aria-label="Breadcrumb">
      <RouterLink class="bj-link" :to="{ name: listRoute(key) }">{{ config.title }}</RouterLink>
      <span aria-hidden="true">/</span>
      <span>{{ route.params.name }}</span>
    </nav>

    <div v-if="loading" class="page__card bj-loading" role="status"><LoadingIndicator /><span>Loading…</span></div>

    <div v-else-if="error" class="page__card">
      <StatePanel
        v-if="error.kind === 'denied'"
        icon="lucide-lock"
        title="This record is unavailable to you"
        message="Your account does not have permission to read this record."
      />
      <StatePanel
        v-else
        icon="lucide-triangle-alert"
        tone="blocked"
        title="The record could not be loaded"
        :message="`${error.message.replace(/[.\s]+$/, '')}. Nothing is shown, because the saved record could not be read.`"
      >
        <button type="button" class="bj-btn bj-btn--primary" @click="load">Try again</button>
      </StatePanel>
    </div>

    <template v-else-if="doc">
      <header class="bj-head">
        <div>
          <h1 class="page__title">{{ title }}</h1>
          <p class="bj-sub">
            <template v-if="title !== doc.name">{{ doc.name }}</template>
            <template v-if="detail.subtitle && doc[detail.subtitle]"><template v-if="title !== doc.name"> · </template>{{ doc[detail.subtitle] }}</template>
          </p>
        </div>
        <div class="bj-toolbar">
          <span v-if="detail.status" class="bj-pill">
            <FieldValue :value="doc[detail.status]" :present="detail.status in doc" type="status" :tones="config.status" />
          </span>
          <span v-if="'docstatus' in doc && doc.docstatus !== 0" class="bj-pill"><FieldValue :value="doc.docstatus" type="docstatus" /></span>
          <a v-if="desk" class="bj-btn" :href="desk"><span class="lucide-external-link" aria-hidden="true" />Open in Desk</a>
        </div>
      </header>

      <div class="bj-grid">
        <article v-for="group in detail.groups" :key="group.title" class="bj-card">
          <h2>{{ group.title }}</h2>
          <dl class="fields">
            <div v-for="field in group.fields" :key="field.field">
              <dt>{{ field.label }}</dt>
              <dd>
                <FieldValue
                  :value="doc[field.field]"
                  :present="field.field in doc"
                  :type="field.type"
                  :to="field.to"
                  :currency="currency"
                  :tones="config.status"
                />
              </dd>
            </div>
          </dl>
        </article>
      </div>

      <section v-for="table in detail.tables ?? []" :key="table.field" class="bj-section">
        <h2>{{ table.title }}</h2>
        <div class="page__card">
          <StatePanel v-if="!Array.isArray(doc[table.field])" icon="lucide-eye-off" :title="`${table.title} unavailable`" message="Your account may not see these rows." />
          <StatePanel v-else-if="!doc[table.field].length" icon="lucide-list" :title="`No ${table.title.toLowerCase()} recorded`" />
          <div v-else class="bj-table-wrap">
            <table class="bj-table bj-table--stack">
              <thead>
                <tr>
                  <th v-for="column in table.columns" :key="column.field" scope="col" :class="{ 'bj-right': right(column) }">{{ column.label }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in doc[table.field]" :key="row.name">
                  <td v-for="column in table.columns" :key="column.field" :data-label="column.label" :class="{ 'bj-right': right(column) }">
                    <FieldValue :value="row[column.field]" :present="column.field in row" :type="column.type" :to="column.to" :currency="currency" />
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <RelatedList v-for="item in related" :key="item.list" :item="item" :value="doc.name" />
    </template>
  </section>
</template>

<style scoped>
.fields {
  display: grid;
  gap: 10px;
  margin: 0;
}
.fields > div {
  display: grid;
  grid-template-columns: minmax(110px, 40%) 1fr;
  gap: 12px;
  font-size: 14px;
}
.fields dt {
  color: var(--bj-muted);
}
.fields dd {
  margin: 0;
  overflow-wrap: anywhere;
}
</style>
