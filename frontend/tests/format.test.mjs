import test from 'node:test'
import assert from 'node:assert/strict'

import { dateText, dateTimeText, fileLink, money, monthText, percentText, recordLink, shiftMonth, sitePath, textValue } from '../src/format.js'
import { sourceText, statusText } from '../src/contracts.js'

test('a missing or withheld amount is "Unavailable", never zero', () => {
  for (const value of [null, undefined, '', 'unavailable', NaN, 'abc', {}]) assert.equal(money(value, 'USD'), 'Unavailable')
  assert.equal(money(0, 'USD'), 'USD 0.00')
  assert.equal(money(9200, 'USD'), 'USD 9,200.00')
  assert.equal(money(1234567.5), '1,234,567.50')
})

test('exact decimal strings from the server are grouped, not re-rounded', () => {
  assert.equal(money('9200.00', 'USD'), 'USD 9,200.00')
  assert.equal(money('12345678901234.56', 'USD'), 'USD 12,345,678,901,234.56')
  assert.equal(money('-1500.5', 'USD'), 'USD -1,500.50')
  assert.equal(money('0.00', 'USD'), 'USD 0.00')
})

test('dates are shown as written by the server, without a time zone shift', () => {
  assert.equal(dateText('2026-11-01'), '1 Nov 2026')
  assert.equal(dateText('2026-12-31 23:59:59.123456'), '31 Dec 2026')
  assert.equal(dateTimeText('2026-11-13T21:37:49+03:00'), '13 Nov 2026, 21:37')
  assert.equal(dateText(null), '—')
  assert.equal(monthText('2026-11'), 'Nov 2026')
  assert.equal(shiftMonth('2026-12', 1), '2027-01')
  assert.equal(shiftMonth('2026-01', -1), '2025-12')
  assert.equal(shiftMonth('2026-11', -11), '2025-12')
})

test('text, percentages and labels', () => {
  assert.equal(textValue(''), 'Unavailable')
  assert.equal(textValue('Synthetic Buyer'), 'Synthetic Buyer')
  assert.equal(percentText(87.456), '87.5%')
  assert.equal(percentText(null), 'Unavailable')
  assert.equal(statusText(1), 'Confirmed')
  assert.equal(statusText(7), 'Unavailable')
  assert.equal(sourceText({ source: 'External (registered)' }), 'External (registered)')
  assert.equal(sourceText({ contract_type: 'Cash' }), 'Cash sale')
})

test('only this site\'s own paths become links', () => {
  assert.equal(fileLink('javascript:alert(1)'), null)
  assert.equal(fileLink('//example.com/files/a.pdf'), null)
  assert.equal(fileLink('/private/files/agreement.pdf'), '/private/files/agreement.pdf')
  assert.equal(sitePath('/app/payment-entry?company=Synthetic'), '/app/payment-entry?company=Synthetic')
  assert.equal(sitePath('//example.com/x'), null)
  assert.equal(sitePath('https://example.com/x'), null)
  assert.equal(sitePath(undefined), null)
  assert.equal(recordLink({ doctype: 'Sidra Sale Contract', name: 'SYNTHETIC/1' }), '/app/sidra-sale-contract/SYNTHETIC%2F1')
  assert.equal(recordLink(null), null)
})
