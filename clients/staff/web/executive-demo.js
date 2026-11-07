// Synthetic management snapshot; all totals and percentages are fixture values.
const report = (path, columns, rows) => ({path, preview: {columns, rows}});
const sales = report('/app/sidra-sale-contract?company=demo&status=Confirmed', ['Contract', 'Property', 'Agreed value'], [
  ['EXT-DEMO-001', 'Demo Plot A-012', 'US$14,000.00'], ['EXT-DEMO-003', 'Demo Plot B-004', 'US$11,000.00'],
]);
const cash = report('/app/payment-entry?company=demo&docstatus=1', ['Receipt', 'Contract', 'Received'], [
  ['DEMO-PAY-001', 'EXT-DEMO-001', 'US$1,250.00'], ['DEMO-PAY-002', 'EXT-DEMO-003', 'US$750.00'],
]);
const aging = report('/app/query-report/Demo%20Contract%20Aging?company=demo', ['Contract', 'Age', 'Unpaid'], [
  ['EXT-DEMO-004', '1–30 days', 'US$4,250.00'], ['EXT-DEMO-005', '31–60 days', 'US$3,000.00'],
]);
const dues = report('/app/query-report/Demo%20Contract%20Dues?company=demo', ['Contract', 'Due date', 'Agreed due'], [
  ['EXT-DEMO-001', '10 Nov 2026', 'US$1,250.00'], ['EXT-DEMO-002', '15 Nov 2026', 'US$2,500.00'],
]);
const jobs = report('/app/sidra-construction-job?company=demo', ['Job', 'Schedule status', 'Milestone'], [
  ['Demo Villa 01', 'On schedule', 'Foundation inspection'], ['Demo House 02', 'At risk', 'Roofing review'],
]);
const units = report('/app/sidra-unit?status=Available', ['Unit', 'Status', 'Asking price'], [
  ['Demo Plot A-018', 'Available', 'US$11,000.00'], ['Demo Plot B-008', 'Available', 'US$11,000.00'],
]);
const reservations = report('/app/sidra-reservation?company=demo', ['Reservation', 'Plot', 'Owner'], [
  ['DEMO-RES-003', 'Demo Plot C-003', 'Demo Sales Manager'],
]);

export default {
  available: true,
  period_label: '1–7 November 2026 · month to date',
  freshness: {status: 'fresh', label: 'Fictional snapshot · current in preview'},
  metrics: {
    sales_value: {available: true, value: '286000', target: '320000', attainment_percent: 89.4, status: 'attention', status_label: 'Below period target', detail: '26 confirmed contracts · commercial value', drilldown: sales},
    cash_collected: {available: true, value: '38500', target: '45000', attainment_percent: 85.6, status: 'attention', status_label: 'Collection follow-up', detail: 'Posted receipts · selected reporting period', drilldown: cash},
    overdue_balance: {available: true, value: '9250', status: 'critical', status_label: '6 contracts overdue', detail: 'Unpaid after allocation · as of snapshot', drilldown: aging},
    due_next_30_days: {available: true, value: '18250', detail: '8 Nov–7 Dec 2026 · unpaid obligations', expected_receipts: {available: false, reason: 'No collection forecast approved'}, drilldown: dues},
    projects_on_schedule: {available: true, value: 7, status: 'attention', status_label: '2 jobs need attention', detail: '7 of 9 active jobs · approved baseline', drilldown: jobs},
    available_units: {available: true, value: 42, asking_value: '462000', detail: 'Asking prices · not asset carrying value', drilldown: units},
  },
  trends: {available: true, period_label: 'Jun–Nov 2026 · Nov to date', months: [
    {label: 'Jun', sales_value: '190000', received: '28000'}, {label: 'Jul', sales_value: '225000', received: '31500'},
    {label: 'Aug', sales_value: '210000', received: '30250'}, {label: 'Sep', sales_value: '248000', received: '36000'},
    {label: 'Oct', sales_value: '270000', received: '41250'}, {label: 'Nov*', sales_value: '286000', received: '38500'},
  ]},
  decisions: {available: true, total: 3, items: [
    {id: 'DEMO-REVIEW-001', priority: 'critical', priority_label: 'Urgent collection', reference: 'EXT-DEMO-004', title: 'Agree a recovery plan for an overdue buyer', impact: {amount: '4250', description: 'unpaid contractual balance'}, owner: 'Demo Finance Lead', due_date: '2026-11-09', next_action: 'Review collection history and assign the next follow-up.', drilldown: report('/app/sidra-sale-contract/DEMO-SSC-004', ['Case', 'Owner', 'Next action'], [['EXT-DEMO-004', 'Demo Finance Lead', 'Review collection history and agree follow-up']])},
    {id: 'DEMO-REVIEW-002', priority: 'attention', priority_label: 'Delivery at risk', reference: 'DEMO-SITE-002', title: 'Resolve the roofing milestone resource gap', impact: {description: 'Completion date at risk · cost impact not yet quantified'}, owner: 'Demo Project Manager', due_date: '2026-11-08', next_action: 'Confirm the recovery programme and responsible site lead.', drilldown: report('/app/sidra-construction-job/DEMO-SITE-002', ['Job', 'Milestone', 'Review needed'], [['Demo House 02', 'Roofing review', 'Resource recovery programme']])},
    {id: 'DEMO-REVIEW-003', priority: 'attention', priority_label: 'Capacity held', reference: '3 reservations', title: 'Review reservations past their follow-up date', impact: {description: '3 plots remain reserved · no automatic release'}, owner: 'Demo Sales Manager', due_date: '2026-11-10', next_action: 'Check each reservation and recommend the next permitted action.', drilldown: reservations},
  ]},
  exposure: {available: true, items: [
    {label: 'Cancelled sales', available: true, value: 2, kind: 'count', detail: 'Selected period · commercial cancellations', drilldown: report('/app/sidra-sale-contract?status=Cancelled', ['Contract', 'Status'], [['EXT-DEMO-090', 'Cancelled'], ['EXT-DEMO-091', 'Cancelled']])},
    {label: 'Reservations needing review', available: true, value: 3, kind: 'count', detail: 'Past their agreed follow-up date', drilldown: reservations},
    {label: 'Available inventory age', available: true, value: 63, kind: 'count', detail: 'Median days available · server-defined age basis', drilldown: report('/app/query-report/Demo%20Inventory%20Age?company=demo', ['Unit', 'Days available'], [['Demo Plot A-018', '45'], ['Demo Plot B-008', '81']])},
    {label: 'Major overdue accounts', available: true, value: '6250', kind: 'money', detail: '4 accounts under management review', drilldown: aging},
  ]},
};
