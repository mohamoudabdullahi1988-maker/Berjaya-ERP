import { ref } from 'vue'

import { boot } from './boot'

// The Companies this user may read, as the server listed them in the boot data, and the one
// the user is looking at. The choice is kept for the session only, in memory.
export const companies = Object.keys(boot?.currencies ?? {}).sort()
export const company = ref(companies.includes(boot?.company) ? boot.company : companies[0] ?? null)
export const currencyOf = (name) => boot?.currencies?.[name] ?? null
