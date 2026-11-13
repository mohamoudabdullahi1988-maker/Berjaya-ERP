import assert from 'node:assert/strict';
import demo from '../web/demo.js';
import calendar from '../web/schedule-demo.js';

// HTTP fixtures exercise UI state and races; Frappe tests cover authorization.
export async function scheduleBrowser({call, js, wait, shot}) {
  const {identifier} = await call('Page.addScriptToEvaluateOnNewDocument', {source: `
    window.__scheduleTest = {dashboard:${JSON.stringify(demo)},calendar:${JSON.stringify(calendar)},requests:[],pending:[],mode:'ok'};
    const original=window.fetch;
    window.fetch=async(url,options)=>{
      const path=String(url),state=window.__scheduleTest;
      if(path.startsWith('/api/method/sidra_realestate.api.staff_dashboard.get_dashboard')) return new Response(JSON.stringify({message:state.dashboard}));
      if(!path.startsWith('/api/method/sidra_realestate.api.staff_dashboard.get_installment_calendar'))return original(url,options);
      const params=Object.fromEntries(new URL(path,location.origin).searchParams);state.requests.push(params);
      const payload=structuredClone(state.calendar);payload.company_id=params.company;payload.month=params.month;
      payload.events=Array.from({length:31},(_,i)=>({...payload.events[1],id:'ROW-'+i,contract_id:'CONTRACT-'+i,external_reference:i===0?'<script>window.owned=true</script>':'EXTERNAL-'+i,due_date:params.month+'-07'}));
      payload.days=[{date:params.month+'-07',amount:'6200.00',count:31}];
      payload.summary={month:{amount:'6200.00',count:31},today:{amount:'6200.00',count:31},past_due:{amount:'0.00',count:0},upcoming:{amount:'0.00',count:0}};
      if(state.mode==='pending')return new Promise(resolve=>state.pending.push(()=>resolve(new Response(JSON.stringify({message:payload})))));
      return new Response(JSON.stringify({message:payload}),{status:state.mode==='denied'?403:200});
    };
  `});
  try {
    await call('Page.navigate', {url:'http://127.0.0.1:4173/'});
    await wait('document.querySelectorAll(".calendar-event").length===2');
    await js('document.querySelector("[data-view=schedule]").click()');
    assert.equal((await js('window.__scheduleTest.requests.at(-1).company')).value,'demo');
    assert((await js('document.querySelector("#schedule-note").textContent')).value.includes('not verified unpaid balances'));
    assert.equal((await js('document.querySelectorAll("#schedule-list tbody tr").length')).value,31);
    assert.equal((await js('Boolean(window.owned)')).value,false,'Server text must not become HTML');
    await shot('installment-calendar-desktop');
    await js('document.querySelector(".calendar-more").click()');
    assert.equal((await js('document.querySelector("#schedule-list").hidden')).value,false);
    assert.equal((await js('document.querySelectorAll("#schedule-list tbody tr").length')).value,31);
    await js('document.querySelector("#schedule-search").value="external-30";document.querySelector("#schedule-search").dispatchEvent(new Event("input"))');
    assert.equal((await js('document.querySelectorAll("#schedule-list tbody tr").length')).value,1);
    await js('document.querySelector("#schedule-search").value="";document.querySelector("#schedule-search").dispatchEvent(new Event("input"));document.querySelector("#schedule-selected-day").click();document.querySelector("[data-schedule-view=calendar]").click()');
    for (const width of [390,320]) {
      await call('Emulation.setDeviceMetricsOverride',{width,height:844,deviceScaleFactor:1,mobile:true});
      assert((await js('document.documentElement.scrollWidth<=innerWidth')).value,`Calendar overflows at ${width}px`);
      if(width===390){await js('document.querySelector(".calendar-wrap").scrollIntoView({block:"center"})');await shot('installment-calendar-mobile');}
      await js('document.querySelector("[data-schedule-view=list]").click()');
      assert((await js('document.documentElement.scrollWidth<=innerWidth')).value,`Schedule list overflows at ${width}px`);
      await js('document.querySelector("[data-schedule-view=calendar]").click()');
    }
    // A late month response may not replace a newer month, even if abort is ignored.
    await js('window.__scheduleTest.mode="pending";document.querySelector("#schedule-prev").click()');
    await wait('window.__scheduleTest.pending.length===1');
    assert.equal((await js('document.querySelectorAll(".calendar-event").length')).value,0);
    await js('window.__scheduleTest.mode="ok";document.querySelector("#schedule-next").click()');
    await wait('document.querySelectorAll(".calendar-event").length===2');
    await js('window.__scheduleTest.pending.shift()();new Promise(resolve=>setTimeout(resolve,50))');
    assert.equal((await js('document.querySelector("#schedule-month").value')).value,'2026-11');
    assert((await js('document.querySelector(".calendar-grid").getAttribute("aria-label")')).value.includes('2026-11'));
    await js('window.__scheduleTest.mode="denied";document.querySelector("#schedule-next").click()');
    await wait('document.querySelector("#schedule-note").textContent.includes("permitted Sidra staff")');
    assert.equal((await js('document.querySelectorAll(".calendar-event,#schedule-list tbody tr").length')).value,0);
    assert.equal((await js('document.querySelectorAll("#schedule-metrics .metric").length')).value,0);
  } finally {
    await call('Page.removeScriptToEvaluateOnNewDocument',{identifier});
  }
}
