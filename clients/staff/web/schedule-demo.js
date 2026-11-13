// Fixed fictional calendar fixture only; never used as a live request fallback.
const rows = [
  ['01', '2026-11-03', '300.00', 'past_due'], ['02', '2026-11-07', '200.00', 'today'],
  ['03', '2026-11-10', '1250.00', 'upcoming'], ['04', '2026-11-15', '2500.00', 'upcoming'], ['05', '2026-11-21', '750.00', 'upcoming'],
];
export default {
  available: true, month: '2026-11', today: '2026-11-07', basis: 'gross_schedule', allocation_available: false,
  notice: 'Fictional calendar preview. Agreed schedule before payment reconciliation; past dates are not verified unpaid balances.',
  summary: {month: {amount: '5000.00', count: 5}, today: {amount: '200.00', count: 1}, past_due: {amount: '300.00', count: 1}, upcoming: {amount: '4500.00', count: 3}},
  days: rows.map(([, day, amount]) => ({date: day, amount, count: 1})),
  events: rows.map(([id, day, amount, state]) => ({id: 'DEMO-ROW-' + id, contract_id: 'DEMO-SSC-' + id, external_reference: 'EXT-DEMO-' + id, customer_display: 'Demo Buyer ' + id, due_date: day, amount, currency: 'USD', row_type: 'Installment', date_state: state})),
};
