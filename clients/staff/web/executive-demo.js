// Synthetic management snapshot; all totals and percentages are fixture values.
const report = (path, columns, rows) => ({path, preview: {columns, rows}});
const pad = value => String(value).padStart(3, '0');
// Complete synthetic cohorts, not partial samples presented as reconciled totals.
// Record generation here is fixture scaffolding, never live financial logic.
const sales = report('/app/sidra-sale-contract?company=demo&status=Confirmed', ['Contract', 'Property', 'Agreed value'],
  [['EXT-DEMO-001', 'Demo Plot A-012', 'US$14,000.00'], ['EXT-DEMO-003', 'Demo Plot B-004', 'US$11,000.00'],
    ...Array.from({length: 24}, (_, i) => [`EXT-DEMO-${101 + i}`, `Demo Plot C-${101 + i}`, i === 23 ? 'US$8,000.00' : 'US$11,000.00'])]);
const cash = report('/app/payment-entry?company=demo&docstatus=1', ['Receipt', 'Contract', 'Received'],
  sales.preview.rows.map((row, i) => [`DEMO-PAY-${pad(i + 1)}`, row[0], ['US$1,250.00', 'US$750.00', 'US$2,000.00'][i] || 'US$1,500.00']));
const aging = report('/app/query-report/Demo%20Contract%20Aging?company=demo', ['Contract', 'Age', 'Unpaid'], [
  ['EXT-DEMO-004', '1–30 days', 'US$4,250.00'], ['EXT-DEMO-005', '31–60 days', 'US$2,000.00'],
  ['EXT-DEMO-006', '31–60 days', 'US$1,000.00'], ['EXT-DEMO-007', '61–90 days', 'US$1,250.00'],
  ['EXT-DEMO-008', '61–90 days', 'US$250.00'], ['EXT-DEMO-009', '90+ days', 'US$500.00'],
]);
const majorAccounts = report('/app/query-report/Demo%20Contract%20Aging?company=demo&management_review=1', aging.preview.columns,
  [aging.preview.rows[0], ...aging.preview.rows.slice(3)]);
const dues = report('/app/query-report/Demo%20Contract%20Dues?company=demo', ['Contract', 'Due date', 'Agreed due'], [
  ['EXT-DEMO-001', '10 Nov 2026', 'US$1,250.00'], ['EXT-DEMO-101', '15 Nov 2026', 'US$2,500.00'],
  ['EXT-DEMO-003', '21 Nov 2026', 'US$750.00'], ['EXT-DEMO-102', '23 Nov 2026', 'US$3,500.00'],
  ['EXT-DEMO-103', '25 Nov 2026', 'US$2,000.00'], ['EXT-DEMO-104', '28 Nov 2026', 'US$3,000.00'],
  ['EXT-DEMO-105', '1 Dec 2026', 'US$2,750.00'], ['EXT-DEMO-106', '7 Dec 2026', 'US$2,500.00'],
]);
const jobs = report('/app/sidra-construction-job?company=demo', ['Job', 'Schedule status', 'Milestone'], [
  ['Demo Villa 01', 'On schedule', 'Foundation inspection'], ['Demo House 02', 'At risk', 'Roofing review'],
  ['Demo House 03', 'Delayed', 'Site recovery review'],
  ...Array.from({length: 6}, (_, i) => [`Demo Villa ${i + 4}`, 'On schedule', 'Planned site review']),
]);
const unitNames = ['Demo Plot A-018', 'Demo Plot B-008', ...Array.from({length: 40}, (_, i) => `Demo Plot D-${pad(i + 1)}`)];
const units = report('/app/sidra-unit?company=demo&status=Available', ['Unit', 'Status', 'Asking price'],
  unitNames.map(name => [name, 'Available', 'US$11,000.00']));
const inventoryAge = report('/app/query-report/Demo%20Inventory%20Age?company=demo', ['Unit', 'Days available'],
  unitNames.map((name, i) => [name, String([45, 81][i] || 63)]));
const reservations = report('/app/sidra-reservation?company=demo', ['Reservation', 'Plot', 'Owner'],
  Array.from({length: 3}, (_, i) => [`DEMO-RES-${pad(i + 1)}`, `Demo Plot R-${pad(i + 1)}`, 'Demo Sales Manager']));

export default {
  available: true,
  period_label: '1–7 November 2026 · month to date',
  freshness: {status: 'fresh', label: 'Fictional snapshot · 7 Nov 2026'},
  metrics: {
    sales_value: {available: true, value: '286000', target: '320000', attainment_percent: 89.4, status: 'attention', status_label: 'Below period target', detail: '26 confirmed contracts · commercial value', drilldown: sales},
    cash_collected: {available: true, value: '38500', target: '45000', attainment_percent: 85.6, status: 'attention', status_label: 'Collection follow-up', detail: 'Posted receipts · selected reporting period', drilldown: cash},
    overdue_balance: {available: true, value: '9250', status: 'critical', status_label: '6 contracts overdue', detail: 'Unpaid after allocation · as of snapshot', drilldown: aging},
    due_next_30_days: {available: true, value: '18250', detail: '8 Nov–7 Dec 2026 · unpaid obligations', expected_receipts: {available: false, reason: 'No collection forecast approved'}, drilldown: dues},
    overdue_milestones: {available:true,value:3,basis:'recorded_stage_dates',detail:'Recorded incomplete stages past their planned end',drilldown:report('/app/sidra-construction-job?company=demo',['Job','Recorded exception'],[['Demo House 02','Roofing'],['Demo House 03','Structure'],['Demo Villa 04','Inspection']])},
    projects_on_schedule: {available: true, value: 7, status: 'attention', status_label: '2 jobs need attention', detail: '7 of 9 active jobs · approved baseline', drilldown: jobs},
    available_units: {available: true, value: 42, asking_value: '462000', detail: 'Asking prices · not asset carrying value', drilldown: units},
  },
  trends: {available: true, period_label: 'Jun–Nov 2026 · Nov to date', months: [
    {label: 'Jun', sales_value: '190000', received: '28000'}, {label: 'Jul', sales_value: '225000', received: '31500'},
    {label: 'Aug', sales_value: '210000', received: '30250'}, {label: 'Sep', sales_value: '248000', received: '36000'},
    {label: 'Oct', sales_value: '270000', received: '41250'}, {label: 'Nov*', sales_value: '286000', received: '38500'},
  ]},
  decisions: {available: true, total: 3, items: [
    {id: 'DEMO-REVIEW-001', priority: 'critical', priority_label: 'Urgent collection', reference: 'EXT-DEMO-004', title: 'Agree a recovery plan for an overdue buyer', impact: {amount: '4250', description: 'unpaid contractual balance'}, owner: 'Demo Finance Lead', due_date: '2026-11-09', next_action: 'Review collection history and assign the next follow-up.', drilldown: report('/app/sidra-sale-contract/DEMO-SSC-004', ['Contract', 'Unpaid', 'Owner', 'Next action'], [['EXT-DEMO-004', 'US$4,250.00', 'Demo Finance Lead', 'Review collection history and assign the next follow-up.']])},
    {id: 'DEMO-REVIEW-002', priority: 'attention', priority_label: 'Delivery at risk', reference: 'DEMO-SITE-002', title: 'Resolve the roofing milestone resource gap', impact: {description: 'Completion date at risk · cost impact not yet quantified'}, owner: 'Demo Project Manager', due_date: '2026-11-08', next_action: 'Confirm the recovery programme and responsible site lead.', drilldown: report('/app/sidra-construction-job/DEMO-SITE-002', ['Job', 'Milestone', 'Review needed'], [['Demo House 02', 'Roofing review', 'Resource recovery programme']])},
    {id: 'DEMO-REVIEW-003', priority: 'attention', priority_label: 'Capacity held', reference: '3 reservations', title: 'Review reservations past their follow-up date', impact: {description: '3 plots remain reserved · no automatic release'}, owner: 'Demo Sales Manager', due_date: '2026-11-10', next_action: 'Check each reservation and recommend the next permitted action.', drilldown: reservations},
  ]},
  exposure: {available: true, items: [
    {label: 'Cancelled sales', available: true, value: 2, kind: 'count', detail: 'Selected period · commercial cancellations', drilldown: report('/app/sidra-sale-contract?status=Cancelled', ['Contract', 'Status'], [['EXT-DEMO-090', 'Cancelled'], ['EXT-DEMO-091', 'Cancelled']])},
    {label: 'Reservations needing review', available: true, value: 3, kind: 'count', detail: 'Past their agreed follow-up date', drilldown: reservations},
    {label: 'Available inventory age', available: true, value: 63, kind: 'count', detail: 'Median days available · server-defined age basis', drilldown: inventoryAge},
    {label: 'Major overdue accounts', available: true, value: '6250', kind: 'money', detail: '4 accounts under management review', drilldown: majorAccounts},
  ]},
};
