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

const amount = value => Number(value.replace(/[^0-9.-]/g, ''));
const rows = metric => demo.executive.metrics[metric].drilldown.preview.rows;
const sum = (records, column) => records.reduce((total, row) => total + amount(row[column]), 0);
test('complete fictional headline supporting cohorts reconcile to the displayed snapshot', () => {
  const metrics = demo.executive.metrics;
  assert.equal(rows('sales_value').length, 26);
  assert.equal(sum(rows('sales_value'), 2), Number(metrics.sales_value.value));
  assert.equal(sum(rows('cash_collected'), 2), Number(metrics.cash_collected.value));
  assert.equal(rows('overdue_balance').length, demo.payments.overdue_contracts);
  assert.equal(sum(rows('overdue_balance'), 2), Number(metrics.overdue_balance.value));
  assert.equal(sum(rows('due_next_30_days'), 2), Number(metrics.due_next_30_days.value));
  assert.equal(rows('projects_on_schedule').length, demo.jobs.active);
  assert.equal(rows('projects_on_schedule').filter(row => row[1] === 'On schedule').length, metrics.projects_on_schedule.value);
  assert.equal(rows('available_units').length, metrics.available_units.value);
  assert.equal(sum(rows('available_units'), 2), Number(metrics.available_units.asking_value));
  assert.equal(demo.executive.trends.months.at(-1).sales_value, metrics.sales_value.value);
  assert.equal(demo.executive.trends.months.at(-1).received, metrics.cash_collected.value);
});

test('fictional exposure and decision evidence use the correct subsets and consistent records', () => {
  const [cancelled, reservations, age, major] = demo.executive.exposure.items;
  assert.equal(cancelled.drilldown.preview.rows.length, cancelled.value);
  assert.equal(reservations.drilldown.preview.rows.length, reservations.value);
  const ages = age.drilldown.preview.rows.map(row => Number(row[1])).sort((a, b) => a - b);
  assert.equal((ages[20] + ages[21]) / 2, age.value);
  assert.equal(major.drilldown.preview.rows.length, 4);
  assert.equal(sum(major.drilldown.preview.rows, 2), Number(major.value));
  for (const row of major.drilldown.preview.rows) assert(rows('overdue_balance').some(overdue => JSON.stringify(overdue) === JSON.stringify(row)));
  const [recovery, , held] = demo.executive.decisions.items;
  assert.equal(amount(recovery.drilldown.preview.rows[0][1]), Number(recovery.impact.amount));
  assert.equal(recovery.reference, recovery.drilldown.preview.rows[0][0]);
  assert.equal(recovery.next_action, recovery.drilldown.preview.rows[0][3]);
  assert.equal(held.drilldown.preview.rows.length, 3);
  const drafts = new Set(demo.contracts.filter(row => row.status === 'Draft').map(row => row.reference));
  assert(rows('due_next_30_days').every(row => !drafts.has(row[0])));
  const soldUnits = new Set([...rows('sales_value').map(row => row[1]), ...demo.contracts.filter(row => row.status === 'Confirmed').map(row => row.unit_label)]);
  assert(rows('available_units').every(row => !soldUnits.has(row[0])));
});
