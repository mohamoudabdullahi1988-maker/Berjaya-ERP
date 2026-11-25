<script setup>
import { ref, useId } from 'vue'

const headingId = useId()
const windowRef = ref(null)
const emit = defineEmits(['open', 'close'])

function close() {
  windowRef.value.close()
}

function open() {
  if (windowRef.value.open) return
  windowRef.value.showModal()
  emit('open')
}
</script>

<template>
  <button type="button" class="bj-btn" aria-label="Open workflow" aria-haspopup="dialog" @click="open">
    <span class="lucide-list-checks" aria-hidden="true" /> Workflow
  </button>
  <dialog ref="windowRef" class="workflow-window" :aria-labelledby="headingId" @close="emit('close')">
    <header>
      <h2 :id="headingId">Workflow</h2>
      <form method="dialog">
        <button type="submit" class="bj-btn bj-btn--icon" aria-label="Close workflow" autofocus>
          <span class="lucide-x" aria-hidden="true" />
        </button>
      </form>
    </header>
    <div class="workflow-content">
      <slot :close="close" />
    </div>
  </dialog>
</template>

<style scoped>
.workflow-window {
  box-sizing: border-box;
  width: min(560px, calc(100vw - 24px));
  max-height: min(740px, calc(100dvh - 24px));
  margin: auto;
  padding: 0;
  overflow: auto;
  border: 1px solid var(--bj-line);
  border-radius: 12px;
  background: var(--bj-card);
  color: var(--bj-ink);
}
.workflow-window::backdrop { background: rgb(31 35 38 / 0.55); }
header {
  position: sticky;
  top: 0;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  border-bottom: 1px solid var(--bj-line);
  background: var(--bj-card);
}
h2 { font-size: 17px; font-weight: 650; }
</style>
