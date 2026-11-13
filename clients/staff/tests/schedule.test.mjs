import test from 'node:test';
import assert from 'node:assert/strict';
import {monthCells, shiftMonth, filterEvents} from '../web/schedule.js';
import fixture from '../web/schedule-demo.js';

test('calendar uses Monday columns and leap-year dates without timezone drift', () => {
  const cells = monthCells('2024-02');
  assert.equal(cells[3], '2024-02-01');
  assert.equal(cells.filter(Boolean).length, 29);
  assert.equal(cells.length % 7, 0);
  assert.equal(monthCells('2026-11')[6], '2026-11-01');
  assert.equal(shiftMonth('2026-12', 1), '2027-01');
  assert.equal(shiftMonth('2026-01', -1), '2025-12');
});

test('calendar and list share search, day and server date-status filters', () => {
  assert.equal(filterEvents(fixture.events, {state: 'past_due'}).length, 1);
  assert.equal(filterEvents(fixture.events, {state: 'today'})[0].due_date, fixture.today);
  assert.equal(filterEvents(fixture.events, {day: '2026-11-15', search: 'BUYER 04'}).length, 1);
  assert.equal(filterEvents(fixture.events, {day: '2026-11-15', state: 'past_due'}).length, 0);
  assert.equal(filterEvents(fixture.events, {search: '<script>'}).length, 0);
});
