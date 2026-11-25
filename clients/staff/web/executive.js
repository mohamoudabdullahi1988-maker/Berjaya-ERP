import {compactMoney, money, date} from './core.js';

export const HEADLINES = [
  {id: 'sales_value', label: 'Confirmed sales value', kind: 'money'},
  {id: 'cash_collected', label: 'Cash collected', kind: 'money'},
  {id: 'overdue_balance', label: 'Overdue balance', kind: 'money'},
  {id: 'due_next_30_days', label: 'Due in the next 30 days', kind: 'money'},
  {id: 'overdue_milestones', label: 'Overdue milestones', kind: 'count'},
  {id: 'available_units', label: 'Available units', kind: 'count'},
];

const numeric = value => (typeof value === 'number' || typeof value === 'string' && value.trim() !== '') && Number.isFinite(Number(value));

// Native ERPNext reports/lists retain their server-side permissions and filters.
export function reportPath(path) {
  if (typeof path !== 'string' || !path.startsWith('/app/') || /[\\\u0000-\u0020\u007f]/.test(path)) return null;
  const url = new URL(path, 'https://sidra.invalid');
  if (url.origin !== 'https://sidra.invalid' || url.hash) return null;
  const route = /^\/app\/(?:query-report\/[^/]+|(?:sidra-sale-contract|sidra-unit|sidra-construction-job|sidra-reservation|payment-entry|lead|opportunity)(?:\/[^/]+)?)$/;
  return route.test(url.pathname) ? url.pathname + url.search : null;
}

export function executiveCards(data) {
  const executive = data?.executive;
  return HEADLINES.map(definition => {
    const metric = executive?.available === true ? executive.metrics?.[definition.id] : null;
    const hasValue = numeric(metric?.value);
    const label = definition.id === 'overdue_balance' && metric?.basis === 'native_invoice_demo' ? 'Overdue invoices (demo)' : definition.id === 'due_next_30_days' && metric?.basis === 'gross_schedule' ? 'Scheduled next 30 days' : definition.label;
    return {...definition, ...(metric || {}), id: definition.id, label, kind: definition.kind,
      available: metric?.available === true && hasValue,
      reason: executive?.available === false ? executive.reason : metric?.reason || 'Executive reporting is not connected yet.'};
  });
}

export function renderExecutive(data, {el, empty, preview}) {
  const $ = id => document.getElementById(id);
  const executive = data?.executive;
  const cards = executiveCards(data);
  const currency = data?.currency || 'USD';
  const usable = executive?.available === true;
  const section = name => usable ? executive[name] : null;
  const format = (value, kind = 'money') => !numeric(value) ? '—' : kind === 'money' ? compactMoney(value, currency) : String(value);
  const stateClass = status => ['on_track', 'attention', 'critical'].includes(status) ? status : 'neutral';

  function openExample(drilldown, title) {
    const sample = drilldown.preview;
    $('evidence-title').textContent = title;
    $('evidence-note').textContent = 'Complete fictional supporting cohort for this fixed preview. Live records require a permission-filtered ERPNext report.';
    $('evidence-body').replaceChildren(el('table', {}, [
      el('thead', {}, el('tr', {}, sample.columns.map(label => el('th', {}, label)))),
      el('tbody', {}, sample.rows.map(row => el('tr', {}, row.map(value => el('td', {}, value))))),
    ]));
    $('evidence-dialog').showModal();
  }

  function linked(tag, attrs, children, drilldown, title) {
    if (preview && drilldown?.preview) return el('a', {...attrs, href: '#supporting-records', onclick: event => {
      event.preventDefault(); openExample(drilldown, title);
    }}, children);
    const path = reportPath(drilldown?.path);
    return path ? el('a', {...attrs, href: path}, children) : el(tag, attrs, children);
  }

  $('metrics').replaceChildren(...cards.map(card => {
    const children = [
      el('div', {class: 'metric-label'}, card.label),
      el('div', {class: 'metric-value' + (card.available ? '' : ' metric-unavailable')}, card.available ? format(card.value, card.kind) : 'Unavailable'),
    ];
    if (card.available && card.status_label) children.push(el('span', {class: 'performance-state ' + stateClass(card.status)}, card.status_label));
    if (card.available && ['sales_value', 'cash_collected'].includes(card.id)) {
      children.push(el('div', {class: 'metric-sub'}, numeric(card.target) ? 'Target ' + money(card.target, currency) : 'Target not set'));
      if (numeric(card.target) && Number.isFinite(card.attainment_percent)) {
        children.push(el('div', {class: 'target-track', role: 'img', 'aria-label': `${card.attainment_percent}% of target`},
          el('span', {style: `width:${Math.max(0, Math.min(100, card.attainment_percent))}%`})),
        el('small', {class: 'target-caption'}, `${card.attainment_percent}% of target`));
      }
    }
    if (card.available && card.id === 'available_units') children.push(el('div', {class: 'metric-sub'}, !numeric(card.asking_value) ? 'Asking value unavailable' : format(card.asking_value) + ' asking value'));
    if (card.available && card.id === 'due_next_30_days') {
      const expected = card.expected_receipts;
      children.push(el('div', {class: 'metric-sub'}, card.basis === 'gross_schedule' ? 'Gross schedule · before settlements, not expected cash' : expected?.available === true && numeric(expected.value) ? 'Expected receipts ' + format(expected.value) : 'Contractual dues · no cash forecast'));
    }
    children.push(el('div', {class: 'metric-sub'}, card.available ? card.detail : card.reason));
    if (card.available && (preview && card.drilldown?.preview || reportPath(card.drilldown?.path))) children.push(el('span', {class: 'records-hint'}, 'View supporting records →'));
    return linked('article', {class: 'metric executive-card' + (card.id === 'cash_collected' ? ' accent' : '')}, children, card.available ? card.drilldown : null, card.label);
  }));

  $('reporting-range').textContent = usable ? executive.period_label || 'Reporting period supplied by server' : 'Awaiting executive reporting';
  const freshness = usable ? executive.freshness : null;
  $('freshness').textContent = freshness?.label || 'Freshness not established';
  $('freshness').className = 'freshness ' + (['fresh', 'stale'].includes(freshness?.status) ? freshness.status : 'unknown');
  $('snapshot-date').textContent = data?.as_of ? 'As of ' + new Intl.DateTimeFormat('en-GB', {
    day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', timeZone: 'Africa/Mogadishu',
  }).format(new Date(data.as_of)) + ' EAT' : 'No server snapshot';

  const trends = section('trends');
  $('trend-range').textContent = trends?.period_label || 'Monthly';
  const months = trends?.available === true && Array.isArray(trends.months) ? trends.months : [];
  const hasNumber = numeric;
  const hasTrend = months.some(month => hasNumber(month.sales_value) || hasNumber(month.received));
  if (!hasTrend) $('executive-trend').replaceChildren(empty(trends?.reason || 'Monthly sales and collection reporting is not connected.'));
  else {
    const scale = Math.max(1, ...months.flatMap(month => [month.sales_value, month.received].filter(hasNumber).map(value => Math.abs(Number(value)))));
    const chart = el('div', {class: 'executive-chart', role: 'img', 'aria-label': 'Monthly confirmed sales value and posted cash collected. Exact values follow in the table.'}, months.map(month =>
      el('div', {class: 'trend-month'}, [el('div', {class: 'trend-pair'}, [['sales_value', 'sales'], ['received', 'cash']].map(([key, style]) =>
        hasNumber(month[key]) ? el('span', {class: 'trend-bar ' + style + (Number(month[key]) < 0 ? ' negative' : ''), style: `height:${Math.max(1, Math.abs(Number(month[key])) / scale * 138)}px`, title: `${month.label}: ${money(month[key], currency)}`}) : el('span', {class: 'trend-missing', title: 'Unavailable'}, '—'))), el('span', {class: 'trend-label'}, month.label)])));
    $('executive-trend').replaceChildren(chart, el('details', {class: 'trend-values'}, [el('summary', {}, 'View exact monthly values'),
      el('div', {class: 'table-wrap'}, el('table', {}, [el('thead', {}, el('tr', {}, ['Month', 'Confirmed sales', 'Cash collected'].map(label => el('th', {}, label)))),
        el('tbody', {}, months.map(month => el('tr', {}, [month.label, numeric(month.sales_value) ? money(month.sales_value, currency) : '—', numeric(month.received) ? money(month.received, currency) : '—'].map(value => el('td', {}, value)))))]))]));
  }

  const decisions = section('decisions');
  $('decision-count').textContent = decisions?.available ? decisions.total != null ? `${decisions.total} open` : 'Partial coverage' : 'Not connected';
  $('decision-list').replaceChildren(...(decisions?.available ? decisions.items?.length ? decisions.items.map(item => {
    const impact = !numeric(item.impact?.amount) ? item.impact?.description || 'Impact not quantified' : money(item.impact.amount, item.impact.currency || currency) + ' · ' + item.impact.description;
    return el('article', {class: 'decision-item'}, [
      el('div', {class: 'decision-heading'}, [el('span', {class: 'performance-state ' + stateClass(item.priority)}, item.priority_label || 'For review'), el('small', {}, item.reference)]),
      el('h3', {}, item.title), el('p', {class: 'decision-impact'}, impact),
      el('div', {class: 'decision-owner'}, [el('span', {}, item.owner || 'Owner not assigned'), el('span', {}, item.due_date ? 'Due ' + date(item.due_date) : 'Deadline not set')]),
      el('p', {class: 'decision-action'}, item.next_action || 'Next action not assigned'),
      linked('span', {class: 'case-link'}, preview && item.drilldown?.preview || reportPath(item.drilldown?.path) ? 'Open case →' : 'Supporting case unavailable', item.drilldown, item.title),
    ]);
  }) : [empty(decisions.summary || 'No escalations in the selected scope.')] : [empty(decisions?.reason || 'Management escalation reporting is not connected.')]));
  if(decisions?.available && decisions.items?.length && decisions.summary) $('decision-list').prepend(el('p',{class:'panel-note footer-note'},decisions.summary));

  const exposure = section('exposure');
  $('executive-exposure').replaceChildren(...(exposure?.available && exposure.items?.length ? exposure.items.map(item =>
    linked('article', {class: 'exposure-item'}, [el('small', {}, item.label),
      el('strong', {}, item.available === true && numeric(item.value) ? format(item.value, item.kind) : 'Unavailable'),
      el('p', {}, item.available ? item.detail : item.reason),
      ...(item.available && (preview && item.drilldown?.preview || reportPath(item.drilldown?.path)) ? [el('span', {class: 'records-hint'}, 'View records →')] : []),
    ], item.available ? item.drilldown : null, item.label)) : [empty(exposure?.reason || 'Cancellation, reservation and inventory-age exposure is not connected.')]));
}
