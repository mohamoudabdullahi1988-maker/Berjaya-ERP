<script setup>
// One look for every non-data state: empty, error, unavailable, not built.
defineProps({
  icon: { type: String, required: true },
  title: { type: String, required: true },
  message: { type: String, default: '' },
  tone: { type: String, default: 'muted' }, // muted | blocked
})
</script>

<template>
  <div class="state" :class="'state--' + tone" role="status">
    <span class="state__icon" :class="icon" aria-hidden="true" />
    <h2 class="state__title">{{ title }}</h2>
    <p v-if="message" class="state__message">{{ message }}</p>
    <div v-if="$slots.default" class="state__actions"><slot /></div>
  </div>
</template>

<style scoped>
.state {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 8px;
  padding: 48px 24px;
  max-width: 460px;
  margin: 0 auto;
}
.state__icon {
  width: 28px;
  height: 28px;
  color: var(--bj-muted);
}
.state--blocked .state__icon {
  color: var(--bj-state-blocked);
}
.state__title {
  margin: 4px 0 0;
  font-size: 17px;
  font-weight: 600;
  color: var(--bj-ink);
}
.state__message {
  margin: 0;
  font-size: 14px;
  line-height: 1.5;
  color: var(--bj-muted);
}
.state__actions {
  margin-top: 12px;
}
</style>
