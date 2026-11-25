<script setup>
import { computed } from 'vue'
import { dateTimeText, recordLink } from '../format.js'
import { actionWords, awaiting, progress, stageLook } from '../workflow.js'

// Fed only by the timeline API. This component draws what it is given: it never works out a
// state, adds a stage, or keeps one after the response it came from is replaced.
const props = defineProps({ timeline: Object, loading: Boolean, error: String })
defineEmits(['refresh'])

const count = computed(() => progress(props.timeline))
const stages = computed(() =>
  (props.timeline?.stages ?? []).map((stage) => ({ stage, look: stageLook(stage), waiting: awaiting(stage) })),
)
</script>

<template>
  <section class="flow" aria-label="Workflow" :aria-busy="loading">
    <div class="flow__top">
      <p v-if="timeline && timeline.supported !== false && !error" class="flow__count">
        <strong>{{ count.done }} of {{ count.total }}</strong> stages complete
      </p>
      <span v-else />
      <button type="button" class="flow__refresh" :disabled="loading" @click="$emit('refresh')">
        <span v-if="loading && timeline" class="flow__spin" aria-hidden="true" /><span v-else class="lucide-refresh-cw" aria-hidden="true" />Refresh
      </button>
    </div>

    <p v-if="loading && !timeline" class="flow__state" role="status">
      <span class="flow__spin" aria-hidden="true" />Loading workflow…
    </p>
    <p v-else-if="error" class="flow__state flow__state--error" role="alert">
      <span class="lucide-triangle-alert" aria-hidden="true" />{{ error }}
    </p>
    <p v-else-if="timeline && timeline.supported === false" class="flow__state">
      <span class="lucide-info" aria-hidden="true" />{{ timeline.reason || 'No workflow is defined for this record.' }}
    </p>

    <ol v-else-if="timeline" class="flow__list">
      <li v-for="{ stage, look, waiting } in stages" :key="stage.key" class="stage" :class="'stage--' + look.kind">
        <span class="stage__icon" :class="look.icon" aria-hidden="true" />
        <div class="stage__body">
          <p class="stage__label">{{ stage.label }}</p>
          <p class="stage__word">{{ look.word }}</p>

          <p v-if="waiting" class="stage__line stage__line--strong">{{ waiting }}</p>
          <p v-if="look.kind === 'current' && actionWords(stage.next_action)" class="stage__line">
            Next: {{ actionWords(stage.next_action) }}
          </p>
          <p v-if="stage.blocker" class="stage__blocker" role="alert">
            <span class="lucide-triangle-alert" aria-hidden="true" />
            <span>{{ stage.blocker.reason }}</span>
          </p>

          <p v-if="stage.unavailable" class="stage__line stage__line--muted">
            <span class="lucide-eye-off" aria-hidden="true" />Unavailable: your account may not see this evidence.
          </p>
          <p v-else-if="stage.detail && look.kind !== 'completed'" class="stage__line stage__line--muted">{{ stage.detail }}</p>

          <details v-if="look.kind === 'completed' && !stage.unavailable" class="stage__more">
            <summary>Details</summary>
            <p v-if="stage.detail">{{ stage.detail }}</p>
            <dl>
              <dt>By</dt>
              <dd>{{ stage.responsible || 'Not recorded' }}</dd>
              <dt>When</dt>
              <dd>{{ stage.timestamp ? dateTimeText(stage.timestamp) : 'Not recorded' }}</dd>
              <template v-if="recordLink(stage.record)">
                <dt>Record</dt>
                <dd><a :href="recordLink(stage.record)">{{ stage.record.name }}</a></dd>
              </template>
            </dl>
          </details>
        </div>
      </li>
    </ol>
  </section>
</template>

<style scoped>
.flow {
  padding: 16px;
  font-size: 14px;
  color: var(--bj-ink);
  overflow-wrap: anywhere;
}
.flow__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 12px;
}
.flow__count {
  margin: 0;
  color: var(--bj-muted);
}
.flow__count strong {
  color: var(--bj-ink);
}
.flow__refresh {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 44px;
  padding: 8px 12px;
  font: inherit;
  font-size: 13px;
  color: var(--bj-ink);
  background: var(--bj-card);
  border: 1px solid var(--bj-line);
  border-radius: 8px;
  cursor: pointer;
}
.flow__refresh:disabled {
  opacity: 0.55;
}
.flow__refresh span,
.flow__state > span,
.stage__line > span {
  flex: none;
  width: 15px;
  height: 15px;
}
.flow__state {
  display: flex;
  gap: 8px;
  margin: 16px 0;
  line-height: 1.45;
  color: var(--bj-muted);
}
.flow__state--error {
  color: var(--bj-state-blocked);
}
.flow__spin {
  flex: none;
  width: 15px;
  height: 15px;
  border: 2px solid var(--bj-line);
  border-top-color: var(--bj-terracotta);
  border-radius: 50%;
  animation: flow-spin 0.7s linear infinite;
}
@keyframes flow-spin {
  to {
    transform: rotate(360deg);
  }
}
@media (prefers-reduced-motion: reduce) {
  .flow__spin {
    animation-duration: 2.4s;
  }
}
.flow__list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.stage {
  position: relative;
  display: grid;
  grid-template-columns: 22px 1fr;
  gap: 12px;
  padding-bottom: 20px;
}
/* The connector to the next stage: solid once this stage is done, dashed otherwise. */
.stage:not(:last-child)::before {
  content: '';
  position: absolute;
  top: 26px;
  bottom: 2px;
  left: 10px;
  border-left: 2px dashed var(--bj-line);
}
.stage--completed:not(:last-child)::before {
  border-left: 2px solid var(--bj-state-completed);
}
.stage__icon {
  width: 22px;
  height: 22px;
  color: var(--bj-state-pending);
}
.stage--completed .stage__icon {
  color: var(--bj-state-completed);
}
.stage--current .stage__icon {
  color: var(--bj-state-current);
}
.stage--blocked .stage__icon {
  color: var(--bj-state-blocked);
}
.stage--skipped .stage__icon {
  color: var(--bj-muted);
}
.stage__body {
  min-width: 0;
}
.stage__body p {
  margin: 0;
}
.stage__label {
  font-weight: 500;
  line-height: 22px;
}
.stage--current .stage__label,
.stage--blocked .stage__label {
  font-weight: 700;
}
.stage--pending .stage__label,
.stage--skipped .stage__label {
  color: var(--bj-muted);
}
.stage__word {
  font-size: 12px;
  color: var(--bj-muted);
}
.stage--current .stage__word {
  color: var(--bj-state-current);
}
.stage--blocked .stage__word {
  color: var(--bj-state-blocked);
}
.stage__line {
  display: flex;
  gap: 6px;
  margin-top: 6px !important;
  font-size: 13px;
  line-height: 1.4;
}
.stage__line--strong {
  font-weight: 500;
}
.stage__line--muted {
  color: var(--bj-muted);
}
.stage__blocker {
  display: flex;
  gap: 8px;
  margin-top: 8px !important;
  padding: 10px 12px;
  font-size: 13px;
  line-height: 1.45;
  color: var(--bj-state-blocked);
  background: var(--bj-state-blocked-tint);
  border: 1px solid var(--bj-state-blocked);
  border-radius: 8px;
}
.stage__blocker > span:first-child {
  flex: none;
  width: 15px;
  height: 15px;
  margin-top: 2px;
}
.stage__more {
  margin-top: 2px;
  font-size: 13px;
}
.stage__more summary {
  display: inline-block;
  padding: 6px 0;
  color: var(--bj-terracotta);
  cursor: pointer;
}
.stage__more p {
  margin: 2px 0 6px;
  color: var(--bj-muted);
}
.stage__more dl {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 2px 12px;
  margin: 0;
}
.stage__more dt {
  color: var(--bj-muted);
}
.stage__more dd {
  margin: 0;
}
.stage__more a {
  color: var(--bj-terracotta);
  text-decoration: underline;
}
</style>
