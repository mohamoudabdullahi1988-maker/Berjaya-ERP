import test from 'node:test';
import assert from 'node:assert/strict';
import {serverOrigin,coordinates,mapLinks,recordPath,requireDashboard,money,compactMoney} from '../web/core.js';
import demo from '../web/demo.js';
test('server connection rejects insecure URLs and embedded credentials',()=>{for(const value of ['http://erp.example.com','https://user:secret@erp.example.com','https://erp.example.com/path','https://erp.example.com?token=secret','javascript:alert(1)'])assert.throws(()=>serverOrigin(value));assert.equal(serverOrigin('https://erp.example.com/'),'https://erp.example.com');});
test('zero is a valid coordinate and invalid pins do not become a fake zero',()=>{assert.deepEqual(coordinates(0,0),{latitude:0,longitude:0});for(const pair of [[null,0],['',0],['   ',0],[true,0],[91,0],[0,181],[NaN,0],['Infinity',0]])assert.throws(()=>coordinates(...pair));});
test('map links contain validated coordinates and fixed Google origins',()=>{const urls=mapLinks(9.5,44);assert.equal(new URL(urls.maps).origin,'https://www.google.com');assert.equal(new URL(urls.maps).searchParams.get('query'),'9.5,44');assert.equal(new URL(urls.earth).origin,'https://earth.google.com');});
test('record navigation cannot introduce a second URL or arbitrary doctype',()=>{assert.equal(recordPath('Sidra Unit','A/B?x=1'),'/app/sidra-unit/A%2FB%3Fx%3D1');assert.throws(()=>recordPath('User','Administrator'));});
test('preview fixture conforms to the server contract',()=>{assert.equal(requireDashboard(demo),demo);assert.throws(()=>requireDashboard({}));});

test('agreed table amounts retain cents',()=>{assert.equal(money('1200.49','USD'),'US$1,200.49');});

test('missing or malformed money never becomes a zero balance',()=>{
 for(const format of [money,compactMoney]){
  for(const amount of [null,undefined,'','  ',true,false,[],{},NaN,Infinity,'Infinity'])assert.equal(format(amount),'—');
  assert.notEqual(format(0),'—');assert.equal(format(0),format('0'));assert.notEqual(format('-12.50'),'—');
 }
});
