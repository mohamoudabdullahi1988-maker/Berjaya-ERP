import assert from 'node:assert/strict';
import demo from '../web/demo.js';

// Browser fixtures verify rendering/request behavior, not Frappe authorization or calculations.
export async function executiveBrowser({call, js, wait, shot}) {
  await call('Page.navigate', {url: 'http://127.0.0.1:4173/?demo=1'});
  await wait('document.querySelectorAll("#metrics .executive-card").length === 6 && document.querySelector("#connection").textContent === "Fictional preview"');
  assert.equal((await js('document.querySelectorAll("#metrics a").length')).value, 6);
  assert.equal((await js('document.querySelectorAll(".trend-month").length')).value, 6);
  assert.equal((await js('document.querySelectorAll(".decision-item").length')).value, 3);
  assert.equal((await js('document.querySelectorAll(".exposure-item").length')).value, 4);
  assert((await js('["company","project","period"].every(id => document.getElementById(id).disabled)')).value);
  for (const [index, count] of [26, 26, 6, 8, 3, 42].entries()) {
    await js(`document.querySelectorAll('#metrics a')[${index}].click()`);
    assert((await js('document.querySelector("#evidence-dialog").open')).value);
    assert.equal((await js('document.querySelectorAll("#evidence-body tbody tr").length')).value, count);
    assert((await js('document.querySelector("#evidence-note").textContent')).value.includes('fictional'));
    await js('document.querySelector("#evidence-dialog button").click()');
  }
  await js('document.querySelectorAll(".case-link")[0].click()');
  assert((await js('document.querySelector("#evidence-body").textContent')).value.includes('4,250'));
  await js('document.querySelector("#evidence-dialog button").click()');
  for (const [index, count] of [2, 3, 42, 4].entries()) {
    await js(`document.querySelectorAll('#executive-exposure a')[${index}].click()`);
    assert.equal((await js('document.querySelectorAll("#evidence-body tbody tr").length')).value, count);
    await js('document.querySelector("#evidence-dialog").close()');
  }
  await call('Emulation.setDeviceMetricsOverride', {width: 1440, height: 1050, deviceScaleFactor: 1, mobile: false});
  await shot('desktop-overview');
  for (const width of [390, 320]) {
    await call('Emulation.setDeviceMetricsOverride', {width, height: 844, deviceScaleFactor: 1, mobile: true});
    assert((await js('document.documentElement.scrollWidth <= innerWidth')).value, `Executive page overflows at ${width}px`);
    await js('document.querySelector(".trend-values").open = true');
    assert((await js('document.documentElement.scrollWidth <= innerWidth')).value, 'Exact trend values overflow the page');
    if (width === 390) await shot('mobile-overview');
  }
  await call('Emulation.setDeviceMetricsOverride', {width: 1440, height: 1050, deviceScaleFactor: 1, mobile: false});

  const fixture = structuredClone(demo);
  fixture.companies.push({id: 'other', name: 'Other fictional company'});
  const {identifier} = await call('Page.addScriptToEvaluateOnNewDocument', {source: `
    window.__executiveTest = {payload: ${JSON.stringify(fixture)}, requests: [], mode: 'ok', pending: []};
    const originalFetch = window.fetch;
    window.fetch = async (url, options) => {
      if (!String(url).startsWith('/api/method/sidra_realestate.api.staff_dashboard.get_dashboard')) return originalFetch(url, options);
      const state = window.__executiveTest;
      const params = Object.fromEntries(new URL(url, location.origin).searchParams);
      state.requests.push(params);
      const payload = structuredClone(state.payload);
      payload.scope.company_id = params.company || 'demo';
      payload.scope.project_id = params.project || null;
      if (payload.executive?.available) {
        payload.executive.period_label = 'Fixture scope: ' + payload.scope.company_id + ' / ' + (params.project || 'all') + ' / ' + params.period;
        payload.executive.metrics.sales_value.drilldown.path = '/app/query-report/Executive%20Sales?' + new URLSearchParams(params);
      }
      if (state.mode === 'pending') return new Promise(resolve => state.pending.push(() => resolve(new Response(JSON.stringify({message:payload})))));
      return new Response(JSON.stringify({message:payload}), {status: state.mode === 'denied' ? 403 : 200});
    };`});
  try {
    await call('Page.navigate', {url: 'http://127.0.0.1:4173/'});
    await wait('window.__executiveTest && document.querySelector("#reporting-range")?.textContent.includes("Fixture scope:")');
    assert((await js('document.querySelector("#demo-banner").hidden')).value);
    assert((await js('document.querySelector("#metrics a").getAttribute("href")')).value.startsWith('/app/query-report/Executive%20Sales?'));
    await js('document.querySelector("#project").value="DEMO-PROJECT-001";document.querySelector("#project").dispatchEvent(new Event("change"))');
    await wait('document.querySelector("#reporting-range").textContent.includes("DEMO-PROJECT-001")');
    await js('document.querySelector("#period").value="last_30_days";document.querySelector("#period").dispatchEvent(new Event("change"))');
    await wait('document.querySelector("#reporting-range").textContent.includes("last_30_days")');
    const query = new URL((await js('document.querySelector("#metrics a").href')).value).searchParams;
    assert.equal(query.get('project'), 'DEMO-PROJECT-001');
    assert.equal(query.get('period'), 'last_30_days');
    await js('document.querySelector("#company").value="other";document.querySelector("#company").dispatchEvent(new Event("change"))');
    await wait('document.querySelector("#reporting-range").textContent.includes("other / all")');
    assert.equal((await js('window.__executiveTest.requests.at(-1).project')).value, undefined);

    // Persisted demo responses are still live responses, with explicit invoice basis.
    await js(`window.__executiveTest.payload.payments={available:true,basis:'native_invoice_demo',received:'35000.00',overdue:'15000.00',collection_rate:70,overdue_invoices:1,overdue_contracts:null,aging:[{label:'1–30 days',amount:'15000.00'}]};
      window.__executiveTest.payload.executive.metrics.overdue_balance.basis='native_invoice_demo';
      document.querySelector('#refresh').click()`);
    await wait('!document.querySelector("#refresh").disabled');
    assert((await js('document.querySelector("#payment-metrics").textContent')).value.includes('Overdue invoices'));
    assert(!(await js('document.querySelector("#payment-metrics").textContent')).value.includes('Overdue contracts'));
    assert((await js('document.querySelector("#metrics").textContent')).value.includes('Overdue invoices (demo)'));
    assert((await js('document.querySelector("#demo-banner").hidden')).value);

    // PR #28 can supply lead counts before qualification stages, and null inspection counts.
    await js(`window.__executiveTest.payload.sales={available:false,reason:'Qualification stages are not defined'};
      window.__executiveTest.payload.summary.new_leads=4;
      Object.assign(window.__executiveTest.payload.jobs,{open:0,active:0,overdue_milestones:0,awaiting_inspection:null,completed:0});
      window.__executiveTest.payload.payments={available:true,received:'0',overdue:' ',collection_rate:null,overdue_contracts:null,aging:[]};
      document.querySelector('#refresh').click()`);
    await wait('!document.querySelector("#refresh").disabled');
    const values = async id => (await js(`Array.from(document.querySelectorAll('#${id} .metric-value'),n=>n.textContent)`)).value;
    assert.equal((await values('sales-metrics'))[0], '4', 'Lead creation does not depend on qualification availability');
    assert.equal((await values('sales-metrics'))[1], 'Unavailable');
    assert.equal((await values('sales-metrics'))[2], 'Unavailable');
    assert((await js('document.querySelector("#pipeline").textContent')).value.includes('Qualification stages are not defined'));
    assert.deepEqual(await values('job-metrics'), ['0','0','0','0']);
    assert((await js('document.querySelector("#job-metrics").textContent')).value.includes('Current records · selected company'));
    const payments = await values('payment-metrics');
    assert.equal(payments[0], 'US$0');
    assert.deepEqual(payments.slice(1), ['Unavailable','Unavailable','Unavailable']);
    await js('window.__executiveTest.payload.summary.new_leads=0;document.querySelector("#refresh").click()');
    await wait('!document.querySelector("#refresh").disabled');
    assert.equal((await values('sales-metrics'))[0], '0');
    await js(`window.__executiveTest.payload.summary.new_leads=null;
      window.__executiveTest.payload.jobs={available:false,reason:'Job access unavailable'};
      window.__executiveTest.payload.payments={available:false,reason:'Payments are not recorded yet'};
      document.querySelector('#refresh').click()`);
    await wait('!document.querySelector("#refresh").disabled');
    assert.equal((await values('sales-metrics'))[0], 'Unavailable');
    assert.deepEqual(await values('job-metrics'), Array(4).fill('Unavailable'));
    assert((await js('document.querySelector("#payment-metrics").textContent')).value.includes('Unavailable'));
    assert((await js('document.querySelector("#aging").textContent')).value.includes('Payments are not recorded yet'));

    await js(`window.__executiveTest.payload.executive.metrics.due_next_30_days.basis='gross_schedule';
      document.querySelector('#refresh').click()`);
    await wait('!document.querySelector("#refresh").disabled');
    const scheduleCard=(await js('document.querySelectorAll("#metrics .executive-card")[3].textContent')).value;
    assert(scheduleCard.includes('Scheduled next 30 days'));
    assert(scheduleCard.includes('before settlements, not expected cash'));
    await js(`window.__executiveTest.payload.executive.decisions={available:true,total:null,items:[],summary:'Partial coverage: reservation data unavailable'};
      document.querySelector('#refresh').click()`);
    await wait('!document.querySelector("#refresh").disabled');
    assert.equal((await js('document.querySelector("#decision-count").textContent')).value,'Partial coverage');
    assert((await js('document.querySelector("#decision-list").textContent')).value.includes('reservation data unavailable'));
    assert(!(await js('document.querySelector("#decision-list").textContent')).value.includes('No escalations'));

    // Missing integration must not borrow totals from the operational summary.
    await js('delete window.__executiveTest.payload.executive;document.querySelector("#refresh").click()');
    await wait('!document.querySelector("#refresh").disabled');
    assert.equal((await js('document.querySelectorAll("#metrics .metric-unavailable").length')).value, 6);
    assert.equal((await js('document.querySelectorAll("#metrics a, .trend-month, .decision-item, .exposure-item").length')).value, 0);

    await js(`window.__executiveTest.payload.executive=${JSON.stringify(fixture.executive)};
      const e=window.__executiveTest.payload.executive;
      e.metrics.sales_value.target=null;e.metrics.cash_collected.value='0';e.metrics.cash_collected.attainment_percent=0;
      e.metrics.available_units.asking_value=' ';e.metrics.due_next_30_days.expected_receipts={available:true,value:' '};
      e.trends.months[0].sales_value=null;e.trends.months[0].received=' ';
      e.freshness={status:'stale',label:'Fixture: collection source is stale'};
      document.querySelector('#refresh').click()`);
    await wait('document.querySelector("#freshness").classList.contains("stale")');
    assert((await js('document.querySelectorAll("#metrics .executive-card")[0].textContent')).value.includes('Target not set'));
    assert(!(await js('document.querySelectorAll("#metrics .executive-card")[1].textContent')).value.includes('Not connected'));
    assert((await js('document.querySelectorAll("#metrics .executive-card")[5].textContent')).value.includes('Asking value unavailable'));
    assert((await js('document.querySelectorAll("#metrics .executive-card")[3].textContent')).value.includes('no cash forecast'));
    assert.equal((await js('document.querySelectorAll(".trend-values tbody tr")[0].textContent')).value, 'Jun——');

    await js('window.__executiveTest.payload.executive.available=false;window.__executiveTest.payload.executive.reason="Management access required";document.querySelector("#refresh").click()');
    await wait('!document.querySelector("#refresh").disabled');
    assert.equal((await js('document.querySelectorAll("#metrics a, .trend-month, .decision-item, .exposure-item").length')).value, 0);
    assert((await js('document.querySelector("#metrics").textContent')).value.includes('Management access required'));

    // Deliberately ignore AbortSignal in the fixture to exercise the generation guard.
    await js(`window.__executiveTest.payload.executive=${JSON.stringify(fixture.executive)};window.__executiveTest.mode='pending';
      document.querySelector('#company').value='demo';document.querySelector('#company').dispatchEvent(new Event('change'))`);
    await wait('window.__executiveTest.pending.length === 1');
    assert.equal((await js('document.querySelectorAll("#metrics a").length')).value, 0);
    await js('window.__executiveTest.mode="ok";document.querySelector("#company").value="other";document.querySelector("#company").dispatchEvent(new Event("change"))');
    await wait('document.querySelector("#reporting-range").textContent.includes("other / all")');
    await js('window.__executiveTest.pending.shift()();new Promise(resolve=>setTimeout(resolve,50))');
    assert((await js('document.querySelector("#reporting-range").textContent')).value.includes('other / all'));
    await js('window.__executiveTest.mode="denied";document.querySelector("#refresh").click()');
    await wait('!document.querySelector("#alert").hidden');
    assert((await js('document.querySelector("#alert").textContent')).value.includes('permitted Sidra staff account'));
    assert.equal((await js('document.querySelectorAll("#metrics a, .trend-month, .decision-item, .exposure-item").length')).value, 0);
    assert((await js('document.querySelector("#demo-banner").hidden')).value);
    assert((await js('document.querySelector("#signout").hidden && !document.querySelector("#signin").hidden')).value);
  } finally {
    await call('Page.removeScriptToEvaluateOnNewDocument', {identifier});
  }
}
