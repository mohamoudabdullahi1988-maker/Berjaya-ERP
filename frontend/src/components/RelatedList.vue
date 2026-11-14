<script setup>
import { onMounted } from 'vue'

import { currencyOf } from '../company'
import { useList } from '../list'
import { RECORDS, listRoute } from '../records'
import FieldValue from './FieldValue.vue'
import ListStates from './ListStates.vue'

// Records of another list that point at this one (e.g. a customer's contracts). Read-only.
const props = defineProps({ item: { type: Object, required: true }, value: { type: String, required: true } })
const config = RECORDS[props.item.list]
const columns = props.item.columns ?? config.list.filter((column) => column.field !== props.item.field)
const fields = [...new Set(['name', ...columns.map((c) => c.field), ...(config.extra ?? [])])]
const LIMIT = 10

const { rows, hasMore, error, state, reload } = useList(config.doctype, {
  fields,
  filters: () => ({ [props.item.field]: props.value }),
  orderBy: props.item.orderBy ?? config.orderBy,
  pageSize: LIMIT,
})
const right = (column) => ['money', 'int', 'number', 'percent'].includes(column.type)
onMounted(reload)
</script>

<template>
  <section class="bj-section">
    <h2>{{ item.title }}</h2>
    <div class="page__card">
      <ListStates :state="state" :error="error" :noun="config.noun ?? item.title.toLowerCase()" :icon="config.icon" :empty-message="`No ${item.title.toLowerCase()} recorded.`" @retry="reload">
        <div class="bj-table-wrap">
          <table class="bj-table bj-table--stack">
            <thead>
              <tr>
                <th v-for="column in columns" :key="column.field" scope="col" :class="{ 'bj-right': right(column) }">{{ column.label }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in rows" :key="row.name">
                <td v-for="column in columns" :key="column.field" :data-label="column.label" :class="{ 'bj-right': right(column) }">
                  <FieldValue
                    :value="row[column.field]"
                    :present="column.field in row"
                    :type="column.type"
                    :to="column.type === 'id' ? item.list : column.to"
                    :name="row.name"
                    :currency="row.currency || currencyOf(row.company)"
                    :tones="config.status"
                  />
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-if="hasMore" class="bj-foot">Showing the latest {{ LIMIT }}. <RouterLink class="bj-link" :to="{ name: listRoute(item.list) }">Open the full list</RouterLink></p>
      </ListStates>
    </div>
  </section>
</template>
