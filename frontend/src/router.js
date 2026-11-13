import { createRouter, createWebHistory } from 'vue-router'

import { canOpen, navItems } from './boot'

const routes = [
  {
    path: '/',
    name: 'home',
    // Land on the first section the server allows; Properties first, as the one built page.
    redirect: () => {
      if (canOpen('properties')) return { name: 'properties' }
      const first = navItems()[0]
      return first ? { name: first.key } : { name: 'no-access' }
    },
  },
  { path: '/properties', name: 'properties', component: () => import('./pages/Properties.vue') },
  { path: '/contracts', name: 'contracts', component: () => import('./pages/Contracts.vue') },
  { path: '/contracts/:name', name: 'contract-detail', component: () => import('./pages/ContractDetail.vue') },
  { path: '/collections', name: 'collections', component: () => import('./pages/Collections.vue') },
  { path: '/construction', name: 'construction', component: () => import('./pages/Construction.vue') },
  { path: '/construction/:name', name: 'construction-detail', component: () => import('./pages/ConstructionDetail.vue') },
  { path: '/finance', name: 'finance', component: () => import('./pages/Finance.vue') },
  { path: '/dashboard', name: 'dashboard', component: () => import('./pages/NotBuilt.vue') },
  { path: '/no-access', name: 'no-access', component: () => import('./pages/NoAccess.vue') },
  { path: '/:rest(.*)*', name: 'not-found', component: () => import('./pages/NotFound.vue') },
]

const router = createRouter({
  history: createWebHistory('/berjaya'),
  routes,
})

const OPEN_TO_ALL = new Set(['home', 'no-access', 'not-found'])
// A detail page belongs to the section whose list it opens from.
const SECTION_OF = { 'contract-detail': 'contracts', 'construction-detail': 'construction' }

// Convenience only: the server refuses the data whatever this guard does.
router.beforeEach((to) => {
  if (OPEN_TO_ALL.has(to.name) || canOpen(SECTION_OF[to.name] ?? to.name)) return true
  return { name: 'no-access' }
})

export default router
