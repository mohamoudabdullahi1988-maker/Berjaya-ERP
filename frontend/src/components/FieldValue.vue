<script setup>
import { computed } from 'vue'

import { dateText, dateTimeText, fileLink, isAmount, money, percentText } from '../format'
import { recordRoute } from '../records'

// Draws one saved value. `present` is false when the server left the field out of the record
// (not readable by this user): that is "Unavailable", never a blank and never zero.
const props = defineProps({
  value: { default: null },
  present: { type: Boolean, default: true },
  type: { type: String, default: 'text' },
  to: { type: String, default: null }, // list key of the linked record, for type "link" / "id"
  name: { type: String, default: null }, // the record's own name, for type "id"
  currency: { type: String, default: null },
  tones: { type: Object, default: null }, // status -> tone
})

const DOCSTATUS = { 0: ['Draft', 'muted'], 1: ['Submitted', 'completed'], 2: ['Cancelled', 'blocked'] }
const empty = (v) => v === null || v === undefined || v === ''

const view = computed(() => {
  const { value, type } = props
  if (!props.present) return { kind: 'unavailable', text: 'Unavailable' }
  if (type === 'docstatus') {
    const [text, tone] = DOCSTATUS[value] ?? ['Unavailable', 'muted']
    return { kind: 'chip', text, tone }
  }
  if (type === 'check') return { kind: 'text', text: value ? 'Yes' : 'No' }
  if (empty(value)) return { kind: 'none', text: '—' }
  switch (type) {
    case 'id':
      return { kind: 'route', text: String(value), route: recordRoute(props.to, props.name) }
    case 'link':
      return { kind: 'route', text: String(value), route: recordRoute(props.to, value) }
    case 'date':
      return { kind: 'text', text: dateText(value) }
    case 'datetime':
      return { kind: 'text', text: dateTimeText(value) }
    case 'money':
      return isAmount(value) ? { kind: 'text', text: money(value, props.currency) } : { kind: 'unavailable', text: 'Unavailable' }
    case 'percent':
      return { kind: 'text', text: percentText(Number(value)) }
    case 'int':
    case 'number':
      return { kind: 'text', text: String(value) }
    case 'status':
      return { kind: 'chip', text: String(value), tone: props.tones?.[value] || 'muted' }
    case 'file': {
      const href = fileLink(value)
      return href ? { kind: 'file', text: value.split('/').pop(), href } : { kind: 'text', text: String(value) }
    }
    case 'longtext':
      return { kind: 'long', text: String(value) }
    default:
      return { kind: 'text', text: String(value) }
  }
})
</script>

<template>
  <span v-if="view.kind === 'unavailable'" class="bj-unavailable" title="Your account may not see this value">Unavailable</span>
  <span v-else-if="view.kind === 'none'" class="bj-muted">—</span>
  <span v-else-if="view.kind === 'chip'" class="bj-chip" :class="'bj-chip--' + view.tone">{{ view.text }}</span>
  <RouterLink v-else-if="view.kind === 'route' && view.route" class="bj-link" :to="view.route">{{ view.text }}</RouterLink>
  <a v-else-if="view.kind === 'file'" class="bj-link" :href="view.href" target="_blank" rel="noopener">{{ view.text }}</a>
  <span v-else-if="view.kind === 'long'" class="long">{{ view.text }}</span>
  <span v-else>{{ view.text }}</span>
</template>

<style scoped>
.long {
  white-space: pre-line;
}
</style>
