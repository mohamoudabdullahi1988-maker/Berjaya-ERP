<script setup>
import { companies, company } from '../company'
</script>

<template>
  <span v-if="companies.length === 1" class="bj-pill">{{ company }}</span>
  <template v-else-if="companies.length > 1">
    <label class="bj-label" for="company-picker">Company</label>
    <select id="company-picker" v-model="company" class="bj-select">
      <option v-for="name in companies" :key="name" :value="name">{{ name }}</option>
    </select>
  </template>
</template>
