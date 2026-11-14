import test from 'node:test'
import assert from 'node:assert/strict'

import { serverMessage, serverMessages } from '../src/api.js'
import {
  HEADER_FIELDS,
  blankForm,
  canConfirm,
  canEdit,
  formFromDoc,
  numberOrNull,
  payloadFromForm,
  savedDifference,
} from '../src/registration.js'

const stage = (key, state, allowed = []) => ({ key, label: key, state, allowed_actions: allowed })

test('edit is offered only when the server lists an edit action', () => {
  assert.equal(canEdit({ stages: [stage('a', 'completed')] }), false)
  assert.equal(canEdit({ stages: [stage('a', 'blocked', ['edit_schedule'])] }), true)
  assert.equal(canEdit({ stages: [stage('a', 'current', ['attach_agreement'])] }), true)
  assert.equal(canEdit(null), false)
})

test('confirm needs the server action and no blocked stage', () => {
  const waiting = { stages: [stage('a', 'completed'), stage('b', 'current', ['confirm_contract'])] }
  assert.equal(canConfirm(waiting), true)
  const blocked = { stages: [stage('a', 'blocked', ['edit_schedule']), stage('b', 'pending', ['confirm_contract'])] }
  assert.equal(canConfirm(blocked), false)
  assert.equal(canConfirm({ stages: [stage('b', 'current')] }), false) // not permitted for this user
  assert.equal(canConfirm(undefined), false)
})

test('the payload holds exactly the fields the server accepts', () => {
  const form = blankForm('Sidra Homes')
  Object.assign(form, { customer: ' Buyer A ', agreed_price: '9,000', installments: '3', external_reference: 'EXT-1' })
  form.units = [{ unit: 'U-1', allocated_price: '9000' }, { unit: '', allocated_price: '' }]
  form.schedule = [
    { row_type: 'Installment', due_date: '2026-02-10', amount: '3000.50' },
    { row_type: 'Fee', due_date: '', amount: '' },
  ]
  const payload = payloadFromForm(form)
  assert.deepEqual(Object.keys(payload).sort(), [...HEADER_FIELDS, 'units', 'schedule'].sort())
  assert.equal(payload.customer, 'Buyer A')
  assert.equal(payload.company, 'Sidra Homes')
  assert.equal(payload.agreed_price, 9000)
  assert.equal(payload.installments, 3)
  assert.equal(payload.due_day, null) // blank: the server's default applies
  assert.equal(payload.contract_profile, null)
  assert.deepEqual(payload.units, [{ unit: 'U-1', allocated_price: 9000 }])
  assert.deepEqual(payload.schedule, [{ row_type: 'Installment', due_date: '2026-02-10', amount: 3000.5 }])
  for (const row of payload.schedule) assert.deepEqual(Object.keys(row).sort(), ['amount', 'due_date', 'row_type'])
})

test('text that is not a number is sent as typed, for the server to refuse', () => {
  assert.equal(numberOrNull('abc'), 'abc')
  assert.equal(numberOrNull(''), null)
  assert.equal(numberOrNull(0), 0)
})

test('a saved contract fills the form without inventing values', () => {
  const doc = {
    name: 'SSC-1',
    customer: 'Buyer A',
    company: 'Sidra Homes',
    agreed_price: 9000,
    down_payment_mode: null,
    contract_profile: null,
    units: [{ unit: 'U-1', allocated_price: 9000, scheme: 'S' }],
    schedule: [{ seq: 1, row_type: 'Installment', due_date: '2026-02-10', amount: 9000, name: 'x' }],
  }
  const form = formFromDoc(doc)
  assert.equal(form.down_payment_mode, 'None')
  assert.equal(form.contract_profile, '')
  assert.deepEqual(form.units, [{ unit: 'U-1', allocated_price: 9000 }])
  assert.deepEqual(form.schedule, [{ row_type: 'Installment', due_date: '2026-02-10', amount: 9000 }])
})

test('the difference shown is the one the server saved', () => {
  assert.equal(savedDifference({ schedule_difference: 0 }), null)
  assert.equal(savedDifference({ schedule_difference: 3.004 }), 3)
  assert.equal(savedDifference({}), null)
})

test('server messages are read as plain text', () => {
  const body = {
    exc_type: 'StaleRecord',
    _server_messages: JSON.stringify([
      JSON.stringify({ message: 'SSC-1 was changed by <b>Hodan</b> after you opened it.', title: 'Message' }),
    ]),
  }
  assert.deepEqual(serverMessages(body), ['SSC-1 was changed by Hodan after you opened it.'])
  assert.equal(serverMessage(body), 'SSC-1 was changed by Hodan after you opened it.')
  assert.equal(serverMessage({ exception: 'frappe.exceptions.ValidationError: Enter the due date' }), 'Enter the due date')
  assert.deepEqual(serverMessages({ _server_messages: 'not json' }), [])
})

test('only a draft registered installment contract is edited on the screen', async () => {
  const { isRegisteredDraft } = await import('../src/registration.js')
  const draft = { docstatus: 0, contract_type: 'Installment', source: 'External (registered)' }
  assert.equal(isRegisteredDraft(draft), true)
  assert.equal(isRegisteredDraft({ ...draft, docstatus: 1 }), false)
  assert.equal(isRegisteredDraft({ ...draft, source: 'Generated from profile' }), false)
  assert.equal(isRegisteredDraft({ ...draft, contract_type: 'Cash' }), false)
  assert.equal(isRegisteredDraft(null), false)
})

const DEFINITION = {
  signing: [{ fieldname: 'notary_name', label: 'Notary', fieldtype: 'Data' }],
  terms: [
    { fieldname: 'penalty_type', label: 'Penalty Type', fieldtype: 'Select', options: ['None', 'Per Day Capped'] },
    {
      fieldname: 'penalty_per_day',
      label: 'Amount per Day',
      fieldtype: 'Currency',
      show_when: { field: 'penalty_type', op: 'eq', values: ['Per Day Capped'] },
    },
    { fieldname: 'refund_compensation', label: 'X', fieldtype: 'Percent', show_when: { field: 'title_refund_after_days', op: 'set', values: [] } },
  ],
  parties: [{ fieldname: 'role', fieldtype: 'Select', options: ['Seller', 'Seller Guarantor', 'Witness'] }],
}

test('term, signing and party fields are sent only with the server definition', async () => {
  const { payloadFromForm, blankForm, blankParty } = await import('../src/registration.js')
  const form = blankForm('C')
  form.extra = { notary_name: ' N ', penalty_type: 'Per Day Capped', penalty_per_day: '5', refund_compensation: '' }
  form.parties = [{ ...blankParty('Seller Guarantor'), full_name: 'G', pledged_property: 'Plot 4' }, blankParty()]
  const without = payloadFromForm(form)
  for (const key of ['notary_name', 'penalty_type', 'parties']) assert.equal(key in without, false)
  const payload = payloadFromForm(form, DEFINITION)
  assert.equal(payload.notary_name, 'N')
  assert.equal(payload.penalty_per_day, 5)
  assert.equal(payload.refund_compensation, null)
  assert.deepEqual(payload.parties, [
    { role: 'Seller Guarantor', full_name: 'G', phone: null, id_number: null, pledged_property: 'Plot 4' },
  ])
})

test('a field applies by the server rule; no rule or an unknown one shows it', async () => {
  const { applies } = await import('../src/registration.js')
  const [, perDay, compensation] = DEFINITION.terms
  assert.equal(applies(perDay, { penalty_type: 'Per Day Capped' }), true)
  assert.equal(applies(perDay, { penalty_type: 'None' }), false)
  assert.equal(applies(compensation, { title_refund_after_days: 0 }), false)
  assert.equal(applies(compensation, { title_refund_after_days: 30 }), true)
  assert.equal(applies({ show_when: { field: 'x', op: 'ne', values: ['None'] } }, { x: '' }), true)
  assert.equal(applies({ show_when: { field: 'x', op: 'mystery', values: [] } }, {}), true)
  assert.equal(applies({}, {}), true)
})

test('the form is dirty only when it differs from the saved record', async () => {
  const { formFromDoc, isDirty } = await import('../src/registration.js')
  const saved = {
    customer: 'B',
    agreed_price: 9000,
    notary_name: 'N',
    parties: [{ role: 'Witness', full_name: 'W' }],
    units: [],
    schedule: [{ row_type: 'Installment', due_date: '2026-02-10', amount: 9000 }],
  }
  const form = formFromDoc(saved, DEFINITION)
  assert.equal(form.extra.notary_name, 'N')
  assert.equal(form.parties[0].full_name, 'W')
  assert.equal(isDirty(form, saved, DEFINITION), false)
  form.schedule[0].amount = '8000'
  assert.equal(isDirty(form, saved, DEFINITION), true)
  assert.equal(isDirty(form, null, DEFINITION), true)
})

test('print opens Frappe print view of the contract', async () => {
  const { printLink } = await import('../src/registration.js')
  assert.equal(printLink('SSC-2026-00001'), '/printview?doctype=Sidra%20Sale%20Contract&name=SSC-2026-00001')
})
