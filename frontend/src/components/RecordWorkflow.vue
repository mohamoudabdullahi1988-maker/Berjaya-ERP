<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'

import { apiGet } from '../api'
import WorkflowPanel from './WorkflowPanel.vue'
import WorkflowWindow from './WorkflowWindow.vue'

const props = defineProps({ doctype: String, name: String, reloadKey: { default: 0 } })
const timeline = ref(null)
const loading = ref(false)
const error = ref('')
const opened = ref(false)
let request = 0

async function load() {
  const id = ++request
  timeline.value = null
  error.value = ''
  loading.value = true
  try {
    const response = await apiGet('/api/method/sidra_realestate.api.record_workflow.get_timeline', {
      doctype: props.doctype,
      name: props.name,
    })
    if (id === request) timeline.value = response.message
  } catch (err) {
    if (id === request) error.value = err.message
  } finally {
    if (id === request) loading.value = false
  }
}

function show() {
  opened.value = true
  load()
}

watch(() => [props.doctype, props.name, props.reloadKey], () => {
  if (opened.value) load()
})
onBeforeUnmount(() => { ++request })
</script>

<template>
  <WorkflowWindow v-slot="{ close }" @open="show" @close="opened = false">
    <WorkflowPanel :timeline="timeline" :loading="loading" :error="error" @refresh="load" />
    <div v-if="timeline?.actions?.length" class="next-actions">
      <h3>Available actions</h3>
      <p>{{ timeline.actions.join(' · ') }}</p>
      <a class="bj-btn" href="#record-actions" @click="close">Go to record actions</a>
    </div>
  </WorkflowWindow>
</template>

<style scoped>
.next-actions { padding: 16px; font-size: 13px; }
</style>
