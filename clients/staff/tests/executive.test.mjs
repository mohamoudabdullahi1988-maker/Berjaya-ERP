import test from 'node:test';
import assert from 'node:assert/strict';
import {executiveCards, reportPath} from '../web/executive.js';
import demo from '../web/demo.js';

test('a legacy dashboard never becomes invented executive totals or targets', () => {
  const legacy = {...demo, executive: undefined};
  const cards = executiveCards(legacy);
  assert.equal(cards.length, 6);
  assert(cards.every(card => !card.available && card.value === undefined && card.target === undefined));
});

test('restricted management data is not exposed through the existing operational summary', () => {
  const restricted = {...demo, executive: {...demo.executive, available: false, reason: 'Management access required'}};
  assert(executiveCards(restricted).every(card => !card.available && card.value === undefined && card.reason === 'Management access required'));
});

test('verified zero is distinct from missing, whitespace and malformed monetary values', () => {
  for (const value of [0, '0']) {
    const data = structuredClone(demo); data.executive.metrics.overdue_balance.value = value;
    assert.equal(executiveCards(data).find(card => card.id === 'overdue_balance').available, true);
  }
  for (const value of [null, undefined, '', '  ', true, [], NaN, 'Infinity']) {
    const data = structuredClone(demo); data.executive.metrics.overdue_balance.value = value;
    assert.equal(executiveCards(data).find(card => card.id === 'overdue_balance').available, false);
  }
});

test('server targets and attainment are preserved without client-side financial calculations', () => {
  const data = structuredClone(demo);
  data.executive.metrics.sales_value.target = null;
  data.executive.metrics.cash_collected.attainment_percent = 121.7;
  const cards = executiveCards(data);
  assert.equal(cards[0].target, null);
  assert.equal(cards[1].attainment_percent, 121.7);
  assert.equal(cards[3].expected_receipts.available, false);
});

test('supporting reports stay on approved native routes with their server filters intact', () => {
  const path = '/app/query-report/Contract%20Aging?company=Demo&project=East&from_date=2026-11-01';
  assert.equal(reportPath(path), path);
  assert.equal(reportPath('/app/sidra-sale-contract/DEMO%2F001'), '/app/sidra-sale-contract/DEMO%2F001');
  for (const value of ['https://evil.example/app/payment-entry', '//evil.example/app/payment-entry', 'javascript:alert(1)', '/api/method/logout', '/app/../api/method/logout', '/app/%2e%2e/api/method/logout', '/app/\\evil.example', '/app/payment-entry#unsafe', '/app/User', '/app/payment-entry\n']) assert.equal(reportPath(value), null);
});
