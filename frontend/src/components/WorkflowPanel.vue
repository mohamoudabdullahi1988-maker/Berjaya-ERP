<script setup>
import { computed } from 'vue'
import { recordLink } from '../contracts'
const props = defineProps({ timeline: Object, loading: Boolean, error: String })
defineEmits(['refresh'])
const complete = computed(() => props.timeline?.stages.filter(s => s.state === 'completed').length || 0)
const icons = { completed: '✓', current: '◉', blocked: '⚠', pending: '○' }
const labels = { completed: 'Completed', current: 'Current', blocked: 'Blocked', pending: 'Pending' }
</script>
<template>
  <section class="workflow" aria-label="Contract workflow" :aria-busy="loading">
    <button type="button" :disabled="loading" @click="$emit('refresh')">Refresh workflow</button>
    <p v-if="loading" role="status">Loading workflow…</p>
    <p v-else-if="error" role="alert">{{ error }}</p>
    <template v-else-if="timeline">
      <p>{{ complete }} of {{ timeline.stages.length }} stages complete</p>
      <p v-if="timeline.supported === false">{{ timeline.reason }}</p>
      <ol>
        <li v-for="stage in timeline.stages" :key="stage.key" :class="stage.state">
          <span class="stage-icon" role="img" :aria-label="labels[stage.state]">{{ icons[stage.state] }}</span>
          <div>
            <strong>{{ stage.label }}</strong><small>{{ labels[stage.state] }}</small>
            <p v-if="stage.detail">{{ stage.detail }}</p>
            <p v-if="stage.unavailable">Unavailable</p>
            <p v-if="stage.skipped">Not required for this contract</p>
            <p v-if="stage.blocker" class="blocker" role="alert">{{ stage.blocker.reason }}</p>
            <details v-if="stage.state === 'completed'">
              <summary>Supporting details</summary>
              <p>{{ stage.responsible || 'Responsible person unavailable' }}</p>
              <p>{{ stage.timestamp || 'Timestamp unavailable' }}</p>
              <a v-if="recordLink(stage.record)" :href="recordLink(stage.record)">{{ stage.record.name }}</a>
            </details>
            <template v-else>
              <p v-if="stage.responsible">{{ stage.responsible }}</p>
              <p v-if="stage.timestamp">{{ stage.timestamp }}</p>
              <a v-if="recordLink(stage.record)" :href="recordLink(stage.record)">{{ stage.record.name }}</a>
            </template>
          </div>
        </li>
      </ol>
    </template>
  </section>
</template>
<style scoped>
.workflow { padding: 16px; font-size: 14px; overflow-wrap: anywhere; color: var(--bj-ink); }
button, summary { min-height: 44px; cursor: pointer; }
button { border: 1px solid var(--bj-line); border-radius: 8px; padding: 8px 12px; }
ol { list-style: none; padding: 0; }
li { display: grid; grid-template-columns: 24px 1fr; gap: 12px; padding: 0 0 24px 8px; border-left: 2px solid var(--bj-line); }
li:last-child { border-left: 0; }
li.pending { border-left-style: dashed; color: var(--bj-muted); }
.stage-icon { font-size: 21px; }
.completed .stage-icon { color: var(--bj-state-completed); }
.current .stage-icon { color: var(--bj-state-current); }
.blocked .stage-icon { color: var(--bj-state-blocked); }
.pending .stage-icon { color: var(--bj-state-pending); }
small { display: block; color: var(--bj-muted); }
p { margin: 8px 0; }
a { color: var(--bj-terracotta); text-decoration: underline; }
.blocker { padding: 12px; border: 1px solid var(--bj-state-blocked); border-radius: 8px; color: var(--bj-state-blocked); }
</style>
