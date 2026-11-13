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
  ...['dashboard', 'collections', 'construction', 'finance'].map((key) => ({
    path: '/' + key,
    name: key,
    component: () => import('./pages/NotBuilt.vue'),
  })),
  { path: '/no-access', name: 'no-access', component: () => import('./pages/NoAccess.vue') },
  { path: '/:rest(.*)*', name: 'not-found', component: () => import('./pages/NotFound.vue') },
]

const router = createRouter({
  history: createWebHistory('/berjaya'),
  routes,
})

const OPEN_TO_ALL = new Set(['home', 'no-access', 'not-found'])

// Convenience only: the server refuses the data whatever this guard does.
router.beforeEach((to) => {
  if (OPEN_TO_ALL.has(to.name) || canOpen(to.name === 'contract-detail' ? 'contracts' : to.name)) return true
  return { name: 'no-access' }
})

export default router
