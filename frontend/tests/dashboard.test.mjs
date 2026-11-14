import test from 'node:test'
import assert from 'node:assert/strict'
import { numeric, format } from '../src/dashboard.js'
test('unknown chart values stay unavailable, never zero', () => {
 for (const value of [null,undefined,'',NaN,false,'unavailable']) { assert.equal(numeric(value),false); assert.equal(format(value,'money','USD'),'Unavailable') }
 assert.equal(format(0,'money','USD'),'USD 0')
 assert.equal(format('1200','money','USD'),'USD 1,200')
 assert.equal(format(-10,'count'),'−10'.replace('−','-'))
})
