import {executiveBrowser} from './executive-browser.mjs';
import {spawn} from 'node:child_process';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import assert from 'node:assert/strict';
const profile=await fs.mkdtemp(path.join(os.tmpdir(),'sidra-ui-'));
const chrome=spawn(process.env.CHROME_BIN||'/usr/bin/chromium',['--headless','--no-sandbox','--disable-dev-shm-usage','--disable-background-networking','--no-proxy-server','--disable-gpu','--remote-debugging-port=9226','--user-data-dir='+profile,'about:blank'],{stdio:'ignore'});
let socket, evaluate;
try{
 for(let i=0;i<60;i++){try{const r=await fetch('http://127.0.0.1:4173/');if(r.ok)break;}catch{}if(i===59)throw Error('Preview server did not become ready');await new Promise(r=>setTimeout(r,150));}
 let pages;for(let i=0;i<60;i++){try{pages=await(await fetch('http://127.0.0.1:9226/json')).json();break;}catch{await new Promise(r=>setTimeout(r,150));}}
 if(!pages)throw Error('Chromium did not start');
 socket=new WebSocket(pages.find(p=>p.type==='page').webSocketDebuggerUrl);await new Promise((r,j)=>{socket.onopen=r;socket.onerror=j;});
 const exceptions=[];
 let id=0;const pending=new Map();socket.onmessage=e=>{const x=JSON.parse(e.data);if(x.method==='Runtime.exceptionThrown')exceptions.push(x.params.exceptionDetails);if(x.id&&pending.has(x.id)){const [resolve,reject]=pending.get(x.id);pending.delete(x.id);x.error?reject(x.error):resolve(x.result);}};
 const call=(method,params={})=>new Promise((r,j)=>{pending.set(++id,[r,j]);socket.send(JSON.stringify({id,method,params}));});
 const js=async expression=>(await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true})).result;
 evaluate=js;
 const wait=async expression=>{for(let i=0;i<70;i++){if((await js(expression)).value)return;await new Promise(r=>setTimeout(r,100));}throw Error('Condition failed: '+expression);};
 await call('Page.enable');await call('Runtime.enable');await call('Emulation.setDeviceMetricsOverride',{width:1440,height:1050,deviceScaleFactor:1,mobile:false});
 const nav=await call('Page.navigate',{url:'http://127.0.0.1:4173/?demo=1'});if(nav.errorText)throw Error(nav.errorText);await wait('document.querySelectorAll(".metric").length>10');
 assert((await js('document.body.innerText')).value.includes('Fictional data'));
 await fs.mkdir('docs/screenshots',{recursive:true});
 const shot=async name=>{await new Promise(r=>setTimeout(r,250));await fs.writeFile('docs/screenshots/'+name+'.png',Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));};
 await shot('desktop-overview');
 await js('document.querySelector("[data-view=payments]").click()');await shot('payments');
 await js('document.querySelector("[data-view=locations]").click();document.querySelector(".location-card").click()');
 assert.equal((await js('document.querySelector(".location-links a").href')).value.startsWith('https://www.google.com/maps/'),true);
 await shot('web-location');
 // Invalid coordinates must not change the pin.
 await js('document.querySelector("[aria-label=Latitude]").value="91";document.querySelector(".location-form").dispatchEvent(new Event("submit",{bubbles:true,cancelable:true}))');
 assert((await js('document.querySelector(".status-message").textContent')).value.includes('Latitude must'));
 await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await js('document.querySelector("[data-view=overview]").click()');await shot('mobile-overview');
 assert((await js('document.documentElement.scrollWidth <= innerWidth')).value,'Mobile page overflows horizontally');
 await call('Page.navigate',{url:'http://127.0.0.1:4173/'});await wait('document.querySelector("#alert") && !document.querySelector("#alert").hidden');
 assert((await js('document.querySelector("#demo-banner").hidden')).value,'Failed live request must not switch to fictional data');
 await executiveBrowser({call,js,wait,shot});
 assert.deepEqual(exceptions, [], 'Unhandled browser exceptions');
 console.log('Browser smoke passed: executive cards/evidence, trends, decisions, exposure, fixed preview, scope requests, stale/missing/restricted data, late responses, 320/390px layout; dashboard, payments, web pin, invalid GPS, mobile width, explicit live failure.');
}catch(error){if(evaluate)console.error('Browser failure page:',(await evaluate('({url:location.href,state:document.readyState,text:document.body?.innerText,html:document.documentElement?.outerHTML.slice(0,1500)})')).value);throw error;}finally{socket?.close();chrome.kill();await fs.rm(profile,{recursive:true,force:true}).catch(()=>{});}
