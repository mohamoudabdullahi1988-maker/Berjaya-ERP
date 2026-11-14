import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile, writeFile, unlink } from 'node:fs/promises'
import { parse, compileScript } from '@vue/compiler-sfc'
import { createSSRApp } from 'vue'
import { renderToString } from 'vue/server-renderer'

import { actionWords, awaiting, progress, stageKind } from '../src/workflow.js'

// The real component is compiled and rendered. Fixtures exist only in this file; the running
// app has no demo or in-memory data.
const source = await readFile(new URL('../src/components/WorkflowPanel.vue', import.meta.url), 'utf8')
const { descriptor } = parse(source)
const compiled = compileScript(descriptor, { id: 'workflow-test', inlineTemplate: true })
const output = new URL('../src/components/.workflow-test.mjs', import.meta.url)
await writeFile(output, compiled.content)
let Panel
try {
  Panel = (await import(output.href)).default
} finally {
  await unlink(output)
}
const render = (props) => renderToString(createSSRApp(Panel, props))

const stage = (key, label, state, extra = {}) => ({
  key, label, state, detail: null, responsible: null, timestamp: null, record: null, blocker: null,
  next_action: null, allowed_actions: [], figures: null, skipped: false, unavailable: false, ...extra,
})
const transaction = { doctype: 'Sidra Sale Contract', name: 'SYN-0001', process: 'external_contract_registration', status: 'Draft' }
const flow = (stages, extra = {}) => ({ transaction, supported: true, reason: null, stages, ...extra })
const LABELS = [
  ['buyer_verified', 'Buyer details verified'],
  ['property_allocation', 'Property allocation checked'],
  ['agreement_attached', 'External agreement attached'],
  ['schedule_validated', 'Installment schedule validated'],
  ['terms_approval', 'Terms approval (Sales Manager)'],
  ['registration_finalized', 'Registration finalized'],
]
const six = (states, extras = {}) => LABELS.map(([key, label], i) => stage(key, label, states[i], extras[key]))
const count = (html, text) => html.split(text).length - 1

test('all completed: six green checks and 6 of 6', async () => {
  const html = await render({
    timeline: flow(six(Array(6).fill('completed'), {
      buyer_verified: { record: { doctype: 'Sidra Customer KYC', name: 'Synthetic Buyer' }, responsible: 'Synthetic Manager', timestamp: '2026-11-01 09:00:00' },
      registration_finalized: { detail: 'Registered as SYN-EXT-0036.' },
    })),
  })
  assert.match(html, /<strong>6 of 6<\/strong> stages complete/)
  assert.equal(count(html, 'lucide-circle-check-big'), 6)
  assert.equal(count(html, 'stage--completed'), 6)
  for (const [, label] of LABELS) assert.ok(html.includes(label))
  assert.ok(html.includes('Registered as SYN-EXT-0036.'))
  assert.ok(html.includes('href="/desk/sidra-customer-kyc/Synthetic%20Buyer"'))
  assert.ok(html.includes('1 Nov 2026, 09:00'))
  assert.ok(!html.includes('role="alert"'))
})

test('stage 1 skipped: not a green check and not counted', async () => {
  const html = await render({
    timeline: flow(six(Array(6).fill('completed'), {
      buyer_verified: { skipped: true, detail: 'Not required for registered contracts. No buyer KYC is on record.' },
    })),
  })
  assert.match(html, /<strong>5 of 6<\/strong> stages complete/)
  assert.equal(count(html, 'lucide-circle-check-big'), 5)
  assert.equal(count(html, 'lucide-circle-minus'), 1)
  assert.ok(html.includes('stage--skipped'))
  assert.ok(html.includes('Not verified - informational'))
  assert.ok(html.includes('No buyer KYC is on record.'))
})

test('stopped at a current stage: ring, who it waits on, next action, no spinner', async () => {
  const html = await render({
    timeline: flow(six(['completed', 'completed', 'completed', 'completed', 'current', 'pending'], {
      terms_approval: { responsible: 'Sidra Sales Manager', next_action: 'confirm_contract', detail: 'Awaiting confirmation by a Sidra Sales Manager.' },
      registration_finalized: { detail: 'After: Terms approval (Sales Manager)' },
    })),
  })
  assert.match(html, /<strong>4 of 6<\/strong> stages complete/)
  assert.equal(count(html, 'lucide-circle-dot'), 1)
  assert.equal(count(html, 'lucide-circle-dashed'), 1)
  assert.ok(html.includes('Awaiting Sidra Sales Manager'))
  assert.ok(html.includes('Next: Confirm contract'))
  assert.ok(html.includes('After: Terms approval (Sales Manager)'))
  assert.ok(!html.includes('flow__spin'))
  assert.ok(!html.includes('Loading workflow'))
})

test('blocked: red icon and the server reason verbatim', async () => {
  const reason = 'The schedule total $ 9,000.00 differs from the amount due $ 10,000.00 by $ 1,000.00; the limit is $ 5.00'
  const html = await render({
    timeline: flow(six(['completed', 'completed', 'completed', 'blocked', 'pending', 'pending'], {
      schedule_validated: { blocker: { reason, action_key: 'edit_schedule' } },
    })),
  })
  assert.match(html, /<strong>3 of 6<\/strong> stages complete/)
  assert.ok(html.includes('stage--blocked'))
  assert.ok(html.includes(reason))
  assert.ok(html.includes('role="alert"'))
  assert.ok(html.includes('Blocked'))
  assert.equal(count(html, 'stage--pending'), 2)
})

test('unavailable: the stage and its state are shown with "Unavailable" for the evidence', async () => {
  const html = await render({
    timeline: flow(six(['completed', 'completed', 'completed', 'completed', 'current', 'pending'], {
      buyer_verified: { unavailable: true, detail: 'Buyer KYC is restricted; its state is unavailable to you.' },
    })),
  })
  assert.ok(html.includes('Buyer details verified'))
  assert.ok(html.includes('Unavailable: your account may not see this evidence.'))
  // No "Details" block for a stage whose evidence is withheld; the other three completed stages have one.
  assert.equal(count(html, '<details'), 3)
})

test('supported false: the reason and no stage list', async () => {
  const html = await render({ timeline: flow([], { supported: false, reason: 'No workflow is defined yet for this kind of contract.' }) })
  assert.ok(html.includes('No workflow is defined yet for this kind of contract.'))
  assert.ok(!html.includes('<ol'))
  assert.ok(!html.includes('stages complete'))
})

test('loading and failure: no stage is shown without a current answer', async () => {
  const loading = await render({ loading: true, timeline: null })
  assert.ok(loading.includes('Loading workflow'))
  assert.ok(loading.includes('flow__spin'))
  const failed = await render({ error: 'You do not have permission to see this workflow.', timeline: null })
  assert.ok(failed.includes('You do not have permission to see this workflow.'))
  assert.ok(!failed.includes('<ol'))
})

test('helpers only map what the server sent', () => {
  assert.equal(stageKind({ state: 'completed', skipped: true }), 'skipped')
  assert.equal(stageKind({ state: 'completed', skipped: false }), 'completed')
  assert.equal(stageKind({ state: 'blocked', skipped: true }), 'blocked')
  assert.equal(stageKind({ state: 'something-new' }), 'pending')
  assert.deepEqual(progress(null), { done: 0, total: 0 })
  assert.equal(actionWords('edit_schedule'), 'Edit schedule')
  assert.equal(actionWords(null), null)
  assert.equal(awaiting({ state: 'completed', responsible: 'System' }), null)
})
