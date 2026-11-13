import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile, writeFile, unlink } from 'node:fs/promises'
import { parse, compileScript } from '@vue/compiler-sfc'
import { createSSRApp } from 'vue'
import { renderToString } from 'vue/server-renderer'
// Compile the actual component; fixtures exist only in this test.
const source = await readFile(new URL('../src/components/WorkflowPanel.vue', import.meta.url), 'utf8')
const { descriptor } = parse(source)
const compiled = compileScript(descriptor, { id: 'workflow-test', inlineTemplate: true })
const output = new URL('../src/components/.workflow-test.mjs', import.meta.url)
await writeFile(output, compiled.content.replace("../contracts\'", "../contracts.js\'"))
let Panel
try { Panel = (await import(output.href)).default } finally { await unlink(output) }
const stage = (state, index) => ({ key: String(index), label: `Stage ${index}`, state, responsible: 'Synthetic reviewer', detail: state === 'current' ? 'Awaiting reviewer' : null, blocker: state === 'blocked' ? { reason: 'Schedule differs by 25.00' } : null })
for (const states of [['completed','completed'], ['completed','current','pending'], ['completed','blocked','pending'], ['current','pending','pending']]) {
  test(states.join(', '), async () => {
    const stages = states.map(stage)
    const html = await renderToString(createSSRApp(Panel, { timeline: { stages } }))
    assert.ok(html.includes(`${states.filter(s => s === 'completed').length} of ${states.length} stages complete`))
    for (const [index, state] of states.entries()) {
      assert.ok(html.includes(`Stage ${index}`))
      assert.ok(html.includes({ completed:'✓', current:'◉', blocked:'⚠', pending:'○' }[state]))
      assert.ok(html.includes(state[0].toUpperCase() + state.slice(1)))
    }
    if (states.includes('blocked')) assert.ok(html.includes('Schedule differs by 25.00'))
    if (states.includes('current')) assert.ok(html.includes('Awaiting reviewer'))
    assert.ok(!html.includes('Loading workflow'))
  })
}
test('loading and failure do not display stale stages', async () => {
  for (const props of [{ loading:true }, { error:'Permission refused' }]) {
    const html = await renderToString(createSSRApp(Panel, { ...props, timeline:{ stages:[stage('completed',0)] } }))
    assert.ok(!html.includes('Stage 0'))
    assert.ok(html.includes(props.loading ? 'Loading workflow' : 'Permission refused'))
  }
})
test('missing amounts and unsafe attachment URLs are not displayed as values', async () => {
  const { money, fileLink, recordLink } = await import('../src/contracts.js')
  for (const value of [null, undefined, '', 'unavailable', NaN]) assert.equal(money(value, 'USD'), 'Unavailable')
  assert.equal(money(0, 'USD'), 'USD 0.00')
  assert.equal(fileLink('javascript:alert(1)'), null)
  assert.equal(fileLink('//example.com/files/a.pdf'), null)
  assert.equal(fileLink('/private/files/agreement.pdf'), '/private/files/agreement.pdf')
  assert.equal(recordLink({ doctype:'Sidra Sale Contract', name:'SYNTHETIC/1' }), '/app/sidra-sale-contract/SYNTHETIC%2F1')
})
