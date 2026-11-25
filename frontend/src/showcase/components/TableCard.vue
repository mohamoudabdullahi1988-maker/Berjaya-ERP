<script setup>
import { computed } from 'vue'

import Card from './Card.vue'
import ReportTable from './ReportTable.vue'

const props = defineProps({ widget: { type: Object, required: true } })
const columns = computed(() => props.widget.columnDefs.map((column) => ({ kind: 'text', ...column })))
const rows = computed(() => props.widget.rows.slice(0, props.widget.limit ?? 10))
</script>

<template>
  <Card :title="widget.title" :note="widget.note" :to="widget.to">
    <ReportTable :columns="columns" :rows="rows" />
  </Card>
</template>
