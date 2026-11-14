// Session facts supplied by the server in www/berjaya.py (window.berjaya_boot). The frontend
// reads them; it never works out permissions for itself.
const raw = window.berjaya_boot

export const boot = raw && typeof raw === 'object' ? raw : null

export function navItems() {
  return boot?.nav ?? []
}

export function canOpen(key) {
  return navItems().some((item) => item.key === key)
}

/** Whether the server says this user may read / create the records of a list (records.js keys). */
export function canRead(list) {
  return Boolean(boot?.lists?.[list]?.read)
}

export function canCreate(list) {
  return Boolean(boot?.lists?.[list]?.create)
}
