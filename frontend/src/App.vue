<script setup>
import { boot } from './boot'
import AppShell from './components/AppShell.vue'
import StatePanel from './components/StatePanel.vue'
import { PRODUCT_NAME } from './brand'
</script>

<template>
  <AppShell v-if="boot">
    <RouterView />
  </AppShell>
  <main v-else class="boot-missing">
    <StatePanel
      icon="lucide-plug-zap"
      tone="blocked"
      :title="`${PRODUCT_NAME} could not start`"
      message="The page did not receive its session details from the server. Reload the page; if this continues, tell your administrator."
    />
  </main>
</template>

<style scoped>
.boot-missing {
  min-height: 100%;
  display: grid;
  place-items: center;
  padding: 24px;
}
</style>
