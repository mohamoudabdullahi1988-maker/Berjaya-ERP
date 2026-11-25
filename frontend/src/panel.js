import { reactive } from 'vue'

// The shell's right-hand panel. A page that fills it calls usePanel(); the shell shows the
// "Workflow" button only while a page is using the panel.
export const panel = reactive({ open: false, inUse: false })

const DESKTOP = '(min-width: 1100px)'

export function claimPanel() {
  panel.inUse = true
  // On a wide screen the panel is a column beside the work, so it opens with the page.
  if (typeof window !== 'undefined' && window.matchMedia(DESKTOP).matches) panel.open = true
}

export function releasePanel() {
  panel.inUse = false
  panel.open = false
}
