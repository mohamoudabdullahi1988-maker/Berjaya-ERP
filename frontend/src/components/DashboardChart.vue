<script setup>
import { computed } from 'vue'
import { format, numeric } from '../dashboard.js'
const props = defineProps({ title: String, note: String, rows: { type: Array, default: () => [] }, currency: String, kind: { type: String, default: 'money' }, tone: { type: String, default: 'terracotta' } })
const maximum = computed(() => Math.max(1, ...props.rows.filter(r => numeric(r.value)).map(r => Math.abs(Number(r.value)))))
</script>
<template>
  <article class="chart-card">
    <h2>{{ title }}</h2><p class="note">{{ note }}</p>
    <p v-if="!rows.length">Unavailable</p>
    <ol v-else class="chart" :aria-label="title">
      <li v-for="(row,index) in rows" :key="index">
        <div class="chart-label"><span>{{ row.label }}</span><strong>{{ format(row.value, kind, currency) }}</strong></div>
        <div v-if="numeric(row.value)" class="track" aria-hidden="true"><span :class="tone" :style="{ width: Math.abs(Number(row.value)) / maximum * 100 + '%' }" /></div>
        <small v-if="numeric(row.value) && Number(row.value) < 0">Negative value; bar shows magnitude</small>
      </li>
    </ol>
  </article>
</template>
<style scoped>
.chart-card { padding: 24px; border: 1px solid var(--bj-line); border-radius: 12px; background: var(--bj-card); min-width: 0; }
h2 { font: 600 19px var(--bj-font-heading); margin: 0 0 8px; }
.note, small { color: var(--bj-muted); font-size: 13px; }
.note { min-height: 40px; }
.chart { padding: 0; list-style: none; display: grid; gap: 18px; }
.chart-label { display: flex; justify-content: space-between; gap: 12px; font-size: 13px; margin-bottom: 7px; }
.chart-label strong { font-variant-numeric: tabular-nums; }
.track { height: 12px; border-radius: 4px; background: var(--bj-ground); overflow: hidden; }
.track span { display: block; height: 100%; background: var(--bj-terracotta); border-radius: 4px; }
.track .blue { background: var(--bj-state-current); }
.track .charcoal { background: var(--bj-charcoal); }
</style>
