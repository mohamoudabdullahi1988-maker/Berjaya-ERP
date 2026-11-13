import {date, money, compactMoney} from './core.js';

export function shiftMonth(month, delta) {
  const [year, number] = month.split('-').map(Number);
  const value = new Date(Date.UTC(year, number - 1 + delta, 1));
  return value.toISOString().slice(0, 7);
}

export function monthCells(month) {
  const [year, number] = month.split('-').map(Number);
  const first = new Date(Date.UTC(year, number - 1, 1));
  const offset = (first.getUTCDay() + 6) % 7;
  const count = new Date(Date.UTC(year, number, 0)).getUTCDate();
  return Array.from({length: Math.ceil((offset + count) / 7) * 7}, (_, index) => {
    const day = index - offset + 1;
    return day >= 1 && day <= count ? `${month}-${String(day).padStart(2, '0')}` : null;
  });
}

export function filterEvents(events, {state = '', search = '', day = ''} = {}) {
  const query = search.trim().toLocaleLowerCase();
  return events.filter(row => (!state || row.date_state === state) && (!day || row.due_date === day) &&
    (!query || [row.contract_id, row.external_reference, row.customer_display].some(value => String(value || '').toLocaleLowerCase().includes(query))));
}

export function createSchedule({el, empty, record, metric, financialMetric, request, preview, getData}) {
  const $ = id => document.getElementById(id);
  let snapshot, company, selectedDay = '', view = 'calendar', generation = 0, aborter;
  const labels = {past_due: 'Past date · unreconciled', today: 'Due today', upcoming: 'Upcoming'};

  function showView() {
    $('schedule-calendar').hidden = view !== 'calendar';
    $('schedule-list').hidden = view !== 'list';
    for (const button of document.querySelectorAll('[data-schedule-view]')) button.setAttribute('aria-pressed', String(button.dataset.scheduleView === view));
  }

  function render() {
    const data = getData();
    if (!snapshot || !data) return;
    const filters = {state: $('schedule-state').value, search: $('schedule-search').value};
    const all = filterEvents(snapshot.events, filters);
    const visible = filterEvents(all, {day: selectedDay});
    $('schedule-note').textContent = snapshot.notice;
    $('schedule-selected-day').textContent = selectedDay ? `Showing ${date(selectedDay)} · clear date filter` : '';
    $('schedule-selected-day').hidden = !selectedDay;
    $('schedule-count').textContent = `${visible.length} scheduled rows${selectedDay ? ' on selected day' : ' in this month'}`;
    $('schedule-metrics').replaceChildren(...[
      ['month', 'Scheduled this month'], ['today', 'Scheduled today'], ['past_due', 'Past scheduled dates'], ['upcoming', 'Upcoming this month'],
    ].map(([key, label]) => {
      const summary = snapshot.summary[key];
      return metric(label, summary.amount == null ? 'Unavailable' : compactMoney(summary.amount, data.currency),
        `${summary.count} agreed rows · before settlements`, false, summary.amount == null);
    }));
    $('schedule-finance').replaceChildren(
      financialMetric('Posted receipts (demo)', data.payments, 'received', 'Selected dashboard period · native receipts'),
      financialMetric('Overdue invoices (demo)', data.payments, 'overdue', 'Current invoice balances · separate from contract schedules'));
    const daily = new Map(snapshot.days.map(day => [day.date, day]));
    const grouped = new Map();
    for (const row of all) {
      if (!grouped.has(row.due_date)) grouped.set(row.due_date, []);
      grouped.get(row.due_date).push(row);
    }
    const choose = day => {selectedDay = day; view = 'list'; render();};
    const headings = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map(day => el('div', {class: 'calendar-weekday'}, day));
    const cells = monthCells(snapshot.month).map(day => {
      if (!day) return el('div', {class: 'calendar-day calendar-blank', 'aria-hidden': 'true'});
      const rows = grouped.get(day) || [];
      const children = [el('button', {class: 'calendar-date', type: 'button', 'aria-label': `Show schedule for ${date(day)}`, onclick: () => choose(day)}, String(Number(day.slice(-2))))];
      if (rows.length) {
        // Daily monetary totals are supplied by the server and apply to the whole day.
        if (!filters.state && !filters.search) children.push(el('small', {class: 'calendar-total'}, money(daily.get(day)?.amount, data.currency)));
        children.push(...rows.slice(0, 2).map(row => el('button', {class: `calendar-event ${row.date_state}`, title: `${row.customer_display} · ${money(row.amount, row.currency)}`, onclick: () => choose(day)}, row.external_reference || row.contract_id)));
        if (rows.length > 2) children.push(el('button', {class: 'calendar-more', onclick: () => choose(day)}, `+${rows.length - 2} more`));
      }
      return el('div', {class: 'calendar-day' + (day === snapshot.today ? ' calendar-today' : '') + (day === selectedDay ? ' calendar-selected' : ''), 'aria-label': `${date(day)}: ${rows.length} scheduled rows`}, children);
    });
    $('schedule-calendar').replaceChildren(el('div', {class: 'calendar-grid', 'aria-label': `Installment calendar ${snapshot.month}`}, [...headings, ...cells]));
    $('schedule-list').replaceChildren(visible.length ? el('table', {}, [
      el('thead', {}, el('tr', {}, ['Contract / buyer', 'Due date', 'Date status', 'Type', 'Agreed amount'].map(label => el('th', {}, label)))),
      el('tbody', {}, visible.map(row => el('tr', {}, [
        el('td', {}, [record('Sidra Sale Contract', row.contract_id, row.external_reference || row.contract_id), el('small', {}, row.customer_display)]),
        el('td', {}, date(row.due_date)), el('td', {}, el('span', {class: `schedule-state ${row.date_state}`}, labels[row.date_state])),
        el('td', {}, row.row_type), el('td', {class: 'number'}, money(row.amount, row.currency)),
      ]))),
    ]) : empty('No scheduled rows match this month and filters.'));
    showView();
  }

  function clear() {
    generation++; aborter?.abort(); snapshot = null;
    for (const id of ['schedule-metrics', 'schedule-finance', 'schedule-calendar', 'schedule-list']) $(id).replaceChildren();
    $('schedule-count').textContent = '';
    $('schedule-selected-day').hidden = true;
    $('schedule-note').textContent = 'Loading permitted schedule records…';
  }

  async function refresh() {
    const data = getData();
    if (!data) {clear(); return;}
    if (company !== data.scope.company_id) {
      company = data.scope.company_id;
      $('schedule-month').value = data.as_of.slice(0, 7);
      $('schedule-state').value = ''; $('schedule-search').value = '';
    }
    selectedDay = '';
    clear(); const current = generation;
    aborter = new AbortController();
    try {
      let result;
      if (preview) result = (await import('./schedule-demo.js')).default;
      else result = await request('sidra_realestate.api.staff_dashboard.get_installment_calendar', {company, month: $('schedule-month').value}, {signal: aborter.signal});
      if (current !== generation || data !== getData()) return;
      if (result?.available !== true) throw new Error(result?.reason || 'Schedule reporting is unavailable.');
      if (!Array.isArray(result.events) || !Array.isArray(result.days) || !result.summary || !/^\d{4}-\d{2}$/.test(result.month)) throw new Error('The schedule response is incompatible.');
      if (!preview && (result.company_id !== company || result.month !== $('schedule-month').value)) throw new Error('Schedule scope does not match the current selection.');
      snapshot = result;
      $('schedule-month').value = result.month;
      render();
    } catch (error) {
      if (error.name === 'AbortError' || current !== generation) return;
      $('schedule-note').textContent = error.message;
      $('schedule-calendar').replaceChildren(empty('Schedule not loaded. Refresh or choose another month.'));
    }
  }

  for (const button of document.querySelectorAll('[data-schedule-view]')) button.addEventListener('click', () => {view = button.dataset.scheduleView; showView();});
  for (const [id, delta] of [['schedule-prev', -1], ['schedule-next', 1]]) {
    $(id).disabled = preview;
    $(id).addEventListener('click', () => {$('schedule-month').value = shiftMonth($('schedule-month').value, delta); refresh();});
  }
  $('schedule-month').disabled = preview;
  $('schedule-month').addEventListener('change', refresh);
  $('schedule-current').disabled = preview;
  $('schedule-current').addEventListener('click', () => {$('schedule-month').value = getData()?.as_of.slice(0, 7) || ''; refresh();});
  $('schedule-state').addEventListener('change', () => {selectedDay = ''; render();});
  $('schedule-search').addEventListener('input', () => {selectedDay = ''; render();});
  $('schedule-selected-day').addEventListener('click', () => {selectedDay = ''; render();});
  return {refresh, clear};
}
