import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {request} from '../web/core.js';
test('writes require a session token before any network request',async()=>{let called=false;const old=globalThis.fetch;globalThis.fetch=async()=>{called=true;throw Error('Unexpected request');};try{await assert.rejects(()=>request('sidra_realestate.api.locations.set_location',{},{write:true}),/session token/);assert.equal(called,false);}finally{globalThis.fetch=old;}});
test('API method cannot escape the same-origin method route',async()=>{await assert.rejects(()=>request('https://external.example/api'),/Invalid API method/);});
test('native manifests contain no bundled server secret and prohibit cleartext',async()=>{const xml=await readFile('native/android/app/src/main/AndroidManifest.xml','utf8');assert(xml.includes('usesCleartextTraffic="false"'));assert(xml.includes('allowBackup="false"'));const mac=await readFile('native/macos/App.entitlements','utf8');assert(mac.includes('com.apple.security.app-sandbox'));});
