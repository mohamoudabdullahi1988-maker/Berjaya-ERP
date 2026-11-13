<script setup>
import StatePanel from '../components/StatePanel.vue'
</script>

<template>
  <section class="page">
    <div class="page__card">
      <StatePanel
        icon="lucide-lock"
        title="Not available to you"
        message="Your account does not have access to this section. Ask your administrator if you need it."
      />
    </div>
  </section>
</template>
