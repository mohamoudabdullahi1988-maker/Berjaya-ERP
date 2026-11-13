<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import StatePanel from '../components/StatePanel.vue'
import { navItems } from '../boot'

const route = useRoute()
const label = computed(() => navItems().find((item) => item.key === route.name)?.label ?? 'This page')
</script>

<template>
  <section class="page">
    <h1 class="page__title">{{ label }}</h1>
    <div class="page__card">
      <StatePanel icon="lucide-construction" title="Not built yet" :message="`${label} has not been built in this interface yet.`" />
    </div>
  </section>
</template>
