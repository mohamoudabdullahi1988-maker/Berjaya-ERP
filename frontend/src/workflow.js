// How a stage returned by the timeline API is drawn. Nothing here decides a state: `state`,
// `skipped` and `unavailable` come from the server and are only mapped to an icon and words.

const LOOK = {
  completed: { icon: 'lucide-circle-check-big', word: 'Completed' },
  current: { icon: 'lucide-circle-dot', word: 'Current' },
  blocked: { icon: 'lucide-triangle-alert', word: 'Blocked' },
  pending: { icon: 'lucide-circle-dashed', word: 'Pending' },
  skipped: { icon: 'lucide-circle-minus', word: 'Not verified - informational' },
}

/** completed | current | blocked | pending | skipped (a completed stage the server marked skipped). */
export function stageKind(stage) {
  if (stage?.state === 'completed' && stage.skipped) return 'skipped'
  return LOOK[stage?.state] ? stage.state : 'pending'
}

export function stageLook(stage) {
  const kind = stageKind(stage)
  return { kind, ...LOOK[kind] }
}

/** "N of M stages complete": skipped stages are not counted as complete. */
export function progress(timeline) {
  const stages = Array.isArray(timeline?.stages) ? timeline.stages : []
  return { done: stages.filter((stage) => stageKind(stage) === 'completed').length, total: stages.length }
}

/** The server's action key in plain words: "confirm_contract" -> "Confirm contract". */
export function actionWords(key) {
  if (typeof key !== 'string' || !key) return null
  const words = key.replaceAll('_', ' ').trim()
  return words.charAt(0).toUpperCase() + words.slice(1)
}

/** A stage waiting on a person says who, e.g. "Awaiting Sidra Sales Manager". */
export function awaiting(stage) {
  return stageKind(stage) === 'current' && stage.responsible ? `Awaiting ${stage.responsible}` : null
}
