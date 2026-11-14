// Registering an External (registered) contract from Berjaya. The server decides everything:
// this file only names the methods, shapes what the form sends, and maps the server's actions
// to buttons. No rule, total or state is worked out here.

export const SAVE_METHOD = 'sidra_realestate.api.contract_registration.save_registration_draft'
export const ATTACH_METHOD = 'sidra_realestate.api.contract_registration.attach_registration_copy'
export const CONFIRM_METHOD = 'sidra_realestate.api.contract_registration.confirm_registration'
export const SIGNED_COPY_FIELD = 'signed_copy'

export const DOWN_PAYMENT_MODES = ['None', 'Included in schedule', 'Recorded separately']
export const ROW_TYPES = ['Installment', 'Down payment', 'Fee']

// The same lists the server accepts (contract_registration.py). Anything else is refused there.
export const HEADER_FIELDS = [
  'customer',
  'company',
  'signed_on',
  'external_reference',
  'agreed_price',
  'contract_profile',
  'down_payment_mode',
  'down_payment',
  'installments',
  'due_day',
  'grace_months',
  'terms_summary',
]
const NUMBERS = new Set(['agreed_price', 'down_payment', 'installments', 'due_day', 'grace_months'])

/** Actions from the timeline that open the edit screen. */
export const EDIT_ACTIONS = ['edit_contract', 'edit_schedule', 'attach_agreement']
export const CONFIRM_ACTION = 'confirm_contract'

/** The actions the server allows this user on any stage of the timeline. */
export function allowedActions(timeline) {
  const found = new Set()
  for (const stage of timeline?.stages ?? []) {
    for (const action of stage.allowed_actions ?? []) found.add(action)
  }
  return found
}

export function canEdit(timeline) {
  const allowed = allowedActions(timeline)
  return EDIT_ACTIONS.some((action) => allowed.has(action))
}

/** Confirm is offered only when the server lists it AND no stage is blocked. The server checks again. */
export function canConfirm(timeline) {
  const stages = timeline?.stages ?? []
  return allowedActions(timeline).has(CONFIRM_ACTION) && !stages.some((stage) => stage.state === 'blocked')
}

/** A draft registered (External) installment contract: the only kind edited on the Berjaya screen. */
export function isRegisteredDraft(doc) {
  return doc?.docstatus === 0 && doc?.contract_type === 'Installment' && String(doc?.source || '').startsWith('External')
}

export function blankRow(rowType = 'Installment') {
  return { row_type: rowType, due_date: '', amount: '' }
}

export function blankUnit() {
  return { unit: '', allocated_price: '' }
}

/** An empty form for a new registration. */
export function blankForm(company = '') {
  return {
    customer: '',
    company: company || '',
    signed_on: '',
    external_reference: '',
    agreed_price: '',
    contract_profile: '',
    down_payment_mode: 'None',
    down_payment: '',
    installments: '',
    due_day: '',
    grace_months: '',
    terms_summary: '',
    units: [blankUnit()],
    schedule: [blankRow()],
  }
}

const shown = (value) => (value === null || value === undefined ? '' : value)

/** The form, filled from a saved contract as the REST API returned it. */
export function formFromDoc(doc) {
  const form = blankForm()
  for (const field of HEADER_FIELDS) form[field] = shown(doc?.[field])
  form.down_payment_mode = doc?.down_payment_mode || 'None'
  form.units = (doc?.units ?? []).map((row) => ({ unit: shown(row.unit), allocated_price: shown(row.allocated_price) }))
  form.schedule = (doc?.schedule ?? []).map((row) => ({
    row_type: row.row_type || 'Installment',
    due_date: shown(row.due_date),
    amount: shown(row.amount),
  }))
  return form
}

/** A typed number as a number; blank stays null so the server's own default applies. */
export function numberOrNull(value) {
  if (value === '' || value === null || value === undefined) return null
  const number = Number(String(value).replace(/,/g, ''))
  return Number.isFinite(number) ? number : String(value) // the server refuses what is not a number
}

const textOrNull = (value) => {
  const text = String(value ?? '').trim()
  return text ? text : null
}

/** Exactly the fields the server accepts, in the form it expects. */
export function payloadFromForm(form) {
  const payload = {}
  for (const field of HEADER_FIELDS) {
    payload[field] = NUMBERS.has(field) ? numberOrNull(form[field]) : textOrNull(form[field])
  }
  payload.down_payment_mode = form.down_payment_mode || 'None'
  payload.units = (form.units ?? [])
    .filter((row) => textOrNull(row.unit) || numberOrNull(row.allocated_price) !== null)
    .map((row) => ({ unit: textOrNull(row.unit), allocated_price: numberOrNull(row.allocated_price) }))
  payload.schedule = (form.schedule ?? [])
    .filter((row) => textOrNull(row.due_date) || numberOrNull(row.amount) !== null)
    .map((row) => ({
      row_type: row.row_type || 'Installment',
      due_date: textOrNull(row.due_date),
      amount: numberOrNull(row.amount),
    }))
  return payload
}

/** One key per form session, so a repeated "Create" after a lost answer makes one draft. */
export function newRequestKey() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID()
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`
}

/** The saved difference between the amount due and the schedule, as the server stored it. */
export function savedDifference(doc) {
  const value = Number(doc?.schedule_difference)
  return Number.isFinite(value) && value !== 0 ? Math.round(value * 100) / 100 : null
}
