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
