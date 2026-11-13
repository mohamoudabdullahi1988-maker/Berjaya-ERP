<script setup>
import { LoadingIndicator } from 'frappe-ui'

import StatePanel from './StatePanel.vue'

// The non-data states every list shares. The default slot is the table, shown when ready.
defineProps({
  state: { type: String, required: true }, // loading | unavailable | error | empty | ready
  error: { type: Object, default: null },
  noun: { type: String, required: true }, // plural, e.g. "construction jobs"
  icon: { type: String, default: 'lucide-inbox' },
  emptyMessage: { type: String, default: '' },
})
defineEmits(['retry'])
const cap = (text) => text.charAt(0).toUpperCase() + text.slice(1)
</script>

<template>
  <div v-if="state === 'loading'" class="bj-loading" role="status"><LoadingIndicator /><span>Loading {{ noun }}…</span></div>
  <StatePanel v-else-if="state === 'unavailable'" icon="lucide-lock" :title="`${cap(noun)} are unavailable to you`" :message="error?.message" />
  <StatePanel
    v-else-if="state === 'error'"
    icon="lucide-triangle-alert"
    tone="blocked"
    :title="`${cap(noun)} could not be loaded`"
    :message="`${(error?.message || 'Something went wrong').replace(/[.\s]+$/, '')}. Nothing is shown, because the saved records could not be read.`"
  >
    <button type="button" class="bj-btn bj-btn--primary" @click="$emit('retry')">Try again</button>
  </StatePanel>
  <StatePanel
    v-else-if="state === 'empty'"
    :icon="icon"
    :title="`No ${noun} on record`"
    :message="emptyMessage || `No ${noun} have been saved yet, or none are visible to your account.`"
  />
  <slot v-else />
</template>
