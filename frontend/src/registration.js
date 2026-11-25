// Registering an External (registered) contract from Berjaya. The server decides everything:
// this file only names the methods, shapes what the form sends, and maps the server's actions
// to buttons. No rule, total or state is worked out here.

export const SAVE_METHOD = 'sidra_realestate.api.contract_registration.save_registration_draft'
export const ATTACH_METHOD = 'sidra_realestate.api.contract_registration.attach_registration_copy'
export const CONFIRM_METHOD = 'sidra_realestate.api.contract_registration.confirm_registration'
export const FILL_METHOD = 'sidra_realestate.api.contract_registration.fill_registration_schedule'
export const FORM_METHOD = 'sidra_realestate.api.contract_registration.get_registration_form'
export const NUMERIC_TYPES = new Set(['Int', 'Float', 'Currency', 'Percent'])
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
    parties: [],
    extra: {}, // term and signing fields, keyed by fieldname, as the server's form lists them
  }
}

export function blankParty(role = 'Witness') {
  return { role, full_name: '', phone: '', id_number: '', pledged_property: '' }
}

const shown = (value) => (value === null || value === undefined ? '' : value)

/** The term and signing fields of the server's form definition (get_registration_form). */
export function extraFields(definition) {
  return [...(definition?.signing ?? []), ...(definition?.terms ?? [])]
}

/** The form, filled from a saved contract as the REST API returned it. */
export function formFromDoc(doc, definition = null) {
  const form = blankForm()
  for (const field of HEADER_FIELDS) form[field] = shown(doc?.[field])
  form.down_payment_mode = doc?.down_payment_mode || 'None'
  form.units = (doc?.units ?? []).map((row) => ({ unit: shown(row.unit), allocated_price: shown(row.allocated_price) }))
  form.schedule = (doc?.schedule ?? []).map((row) => ({
    row_type: row.row_type || 'Installment',
    due_date: shown(row.due_date),
    amount: shown(row.amount),
  }))
  form.parties = (doc?.parties ?? []).map((row) => ({
    role: row.role || 'Witness',
    full_name: shown(row.full_name),
    phone: shown(row.phone),
    id_number: shown(row.id_number),
    pledged_property: shown(row.pledged_property),
  }))
  for (const field of extraFields(definition)) form.extra[field.fieldname] = shown(doc?.[field.fieldname])
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

/** Exactly the fields the server accepts, in the form it expects. Term, signing and party
 * fields are sent only when the server's form definition was loaded, so a failed load never
 * blanks values the screen could not show. */
export function payloadFromForm(form, definition = null) {
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
  if (definition) {
    for (const field of extraFields(definition)) {
      const value = form.extra?.[field.fieldname]
      payload[field.fieldname] = NUMERIC_TYPES.has(field.fieldtype) ? numberOrNull(value) : textOrNull(value)
    }
    payload.parties = (form.parties ?? [])
      .filter((row) => textOrNull(row.full_name) || textOrNull(row.phone) || textOrNull(row.id_number))
      .map((row) => ({
        role: row.role || 'Witness',
        full_name: textOrNull(row.full_name),
        phone: textOrNull(row.phone),
        id_number: textOrNull(row.id_number),
        pledged_property: textOrNull(row.pledged_property),
      }))
  }
  return payload
}

/** Whether a field applies, by the plain rule the server derived from the DocType. No rule, or
 * one the server could not read, means the field is shown. */
export function applies(field, values) {
  const rule = field?.show_when
  if (!rule) return true
  const current = values?.[rule.field]
  const text = current === null || current === undefined ? '' : String(current)
  if (rule.op === 'eq') return rule.values.includes(text)
  if (rule.op === 'ne') return !rule.values.includes(text)
  if (rule.op === 'in') return rule.values.includes(text)
  if (rule.op === 'set') return text !== '' && text !== '0'
  return true
}

/** Whether the form differs from what was last saved. */
export function isDirty(form, saved, definition) {
  if (!saved) return true
  return JSON.stringify(payloadFromForm(form, definition)) !== JSON.stringify(payloadFromForm(formFromDoc(saved, definition), definition))
}

/** Frappe's own print view of the contract (its default print format). */
export function printLink(name) {
  return '/printview?doctype=' + encodeURIComponent('Sidra Sale Contract') + '&name=' + encodeURIComponent(name)
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
