import {coordinates,mapLinks,money,compactMoney,date,recordPath,requireDashboard,request} from './core.js';
import {renderExecutive} from './executive.js';
const $ = id => document.getElementById(id);
const preview = new URLSearchParams(location.search).get('demo') === '1';
const config = window.SIDRA_CONFIG;
let data, active = 'overview', selectedLocation, aborter, loadGeneration = 0;
const names = {overview:'Executive overview',sales:'Sales pipeline',payments:'Payments',jobs:'Construction jobs',contracts:'Contracts',schedule:'Installment schedule',locations:'Plots & site locations'};
function el(tag, attrs={}, children=[]) {
 const n=document.createElement(tag);
 for(const [k,v] of Object.entries(attrs)) {
  if(k.startsWith('on')) n.addEventListener(k.slice(2),v);
  else if(k==='class') n.className=v;
  else if(v!==false && v!=null) n.setAttribute(k,v===true?'':String(v));
 }
 for(const child of (Array.isArray(children)?children:[children])) if(child!=null)n.append(child instanceof Node?child:document.createTextNode(String(child)));
 return n;
}
function message(text) {$('alert').textContent=text;$('alert').hidden=!text;}
function empty(text) {return el('div',{class:'empty'},text);}
function go(view) {
 if(!names[view])return;
 active=view;
 for(const s of document.querySelectorAll('.view'))s.hidden=s.id!=='view-'+view;
 for(const b of document.querySelectorAll('.nav'))b.classList.toggle('active',b.dataset.view===view);
 $('breadcrumb').replaceChildren('Workspace ',el('span',{},'/'),names[view]);
 $('page-title').textContent=({overview:'Sales. Cash. Delivery.',sales:'From first enquiry to agreement.',payments:'Know what’s paid. See what’s due.',jobs:'Every milestone in view.',contracts:'Agreements, kept together.',schedule:'The dates you agreed.',locations:'A place for every property.'})[view];
 $('eyebrow').textContent=view==='overview'?'THE MANAGEMENT VIEW':names[view].toUpperCase();
 $('subtitle').textContent=view==='overview'?'Performance, exposure and the decisions that need you.':view==='locations'?'One saved location, shared across web, Android and Mac.':'Server-controlled information for your permitted company and reporting period.';
}
for(const b of document.querySelectorAll('[data-view]'))b.addEventListener('click',()=>go(b.dataset.view));
function arrow() {const s=document.createElementNS('http://www.w3.org/2000/svg','svg');s.setAttribute('viewBox','0 0 24 24');s.setAttribute('width','15');s.setAttribute('height','15');s.setAttribute('aria-hidden','true');const p=document.createElementNS(s.namespaceURI,'path');p.setAttribute('d','M6 18 18 6M6 6h12v12');p.setAttribute('fill','none');p.setAttribute('stroke','currentColor');p.setAttribute('stroke-width','1.4');s.append(p);return s;}
function metric(label,value,note,accent=false,unavailable=false) {return el('article',{class:'metric'+(accent?' accent':'')},[el('div',{class:'metric-label'},[label,arrow()]),el('div',{class:unavailable?'metric-value metric-unavailable':'metric-value'},value),el('div',{class:'metric-sub'},note)]);}
function unavailable(group) {return !group?.available;}
function financialMetric(label,group,key,note) {
 if(unavailable(group))return metric(label,'Awaiting finance integration',group?.reason||'Posted payment data has not been connected.',false,true);
 const value=compactMoney(group[key],data.currency),known=value!=='—';
 return metric(label,known?value:'Unavailable',known?note:'This amount is unavailable.',false,!known);
}
function countMetric(label,value,note,reason='This count is unavailable.') {
 const known=Number.isInteger(value)&&value>=0;
 return metric(label,known?value:'Unavailable',known?note:reason,false,!known);
}
function percentageMetric(label,value,note) {
 const known=typeof value==='number'&&Number.isFinite(value);
 return metric(label,known?`${value}%`:'Unavailable',known?note:'This rate is unavailable.',false,!known);
}
function cells(row) {return row.map(v=>el('td',{},v));}
function table(headers,rows) {if(!rows.length)return empty('No records for this company and period.');return el('table',{},[el('thead',{},el('tr',{},headers.map(h=>el('th',{},h)))),el('tbody',{},rows.map(row=>el('tr',{},cells(row))))]);}
function record(doctype,id,label) {
 if(preview)return el('span',{},[label,el('small',{},'Fictional preview record')]);
 return el('a',{href:recordPath(doctype,id)},label);
}
function contracts(rows) {return table(['Reference / buyer','Property','Agreed value','Status','Signing date'],rows.map(r=>[el('div',{},[record('Sidra Sale Contract',r.id,r.reference||r.id),el('small',{},r.customer_display)]),r.unit_label,el('span',{class:'number'},money(r.value,r.currency)),el('span',{class:'status'+(r.status==='Draft'?' draft':'')},r.status),date(r.signed_on)]));}
function pipeline(target,rows,currency=false) {$(target).replaceChildren(...rows.map(r=>el('div',{class:'pipeline-item'},[el('small',{},r.label),el('b',{},currency?money(r.amount,data.currency):r.value)])));}
function render() {
 $('signin').hidden=true;$('signout').hidden=preview;
 $('connection').textContent=preview?'Fictional preview':'Connected to ERPNext';
 $('role').textContent=data.scope.role_label||'Staff workspace';
 $('updated').textContent='As of '+new Intl.DateTimeFormat('en-GB',{hour:'2-digit',minute:'2-digit',timeZone:'Africa/Mogadishu'}).format(new Date(data.as_of))+' EAT';
 $('company').replaceChildren(...data.companies.map(c=>el('option',{value:c.id,selected:c.id===data.scope.company_id},c.name)));
 const projects = data.projects || [];
 $('project').replaceChildren(el('option',{value:''},'All permitted projects'),...projects.map(p=>el('option',{value:p.id,selected:p.id===data.scope.project_id},p.name)));
 $('company').disabled=preview;$('period').disabled=preview;
 $('project').disabled=preview||!projects.length;
 renderExecutive(data,{el,empty,preview});
 renderContracts();
 $('upcoming').replaceChildren(table(['Contract / buyer','Due date','Type','Agreed amount'],data.schedule.upcoming.map(r=>[el('div',{},[record('Sidra Sale Contract',r.contract_id,r.external_reference||r.contract_id),el('small',{},r.customer_display)]),date(r.due_date),r.row_type,money(r.amount,r.currency)])));
 $('sales-metrics').replaceChildren(countMetric('New leads',data.summary.new_leads,'Created during the selected period'),countMetric('Qualified opportunities',data.sales?.available?data.sales.qualified_opportunities:null,'Server qualification status',data.sales?.reason),percentageMetric('Lead conversion',data.sales?.available?data.sales.conversion_rate:null,'Server-linked lead cohort'),metric('Agreed contract value',compactMoney(data.summary.agreed_contract_value,data.currency),'Commercial value · not recognized revenue',true));
 if(data.sales?.available)pipeline('pipeline',data.sales.pipeline);else $('pipeline').replaceChildren(empty(data.sales?.reason||'Lead integration is not connected yet.'));
 $('payment-metrics').replaceChildren(financialMetric('Payments received',data.payments,'received','Posted receipts only'),financialMetric('Overdue unpaid',data.payments,'overdue','After payment allocation'),percentageMetric('Collection rate',data.payments?.available?data.payments.collection_rate:null,'Server-defined due cohort'),countMetric('Overdue contracts',data.payments?.available?data.payments.overdue_contracts:null,'With unpaid overdue obligations',data.payments?.reason));
 if(data.payments?.available)pipeline('aging',data.payments.aging,true);else $('aging').replaceChildren(empty(data.payments?.reason||'Awaiting finance integration. Schedule amounts are not evidence of payment or arrears.'));
 $('job-metrics').replaceChildren(...[['Active jobs','active'],['Overdue milestones','overdue_milestones'],['Awaiting inspection','awaiting_inspection'],['Completed jobs','completed']].map(([label,key])=>countMetric(label,data.jobs?.available?data.jobs[key]:null,'Current records · selected company',data.jobs?.reason)));
 $('jobs-table').replaceChildren(data.jobs?.available?table(['Job','Status','Progress','Next milestone','Due date'],data.jobs.items.map(r=>[record('Sidra Construction Job',r.id,r.label),r.status,r.progress==null?'—':`${r.progress}%`,r.next_milestone,date(r.due_date)])):empty('Job reporting is supplied by the server.'));
 renderLocations();
}
function renderContracts() {if(!data)return;const q=$('contract-search').value.toLocaleLowerCase();$('contracts-table').replaceChildren(contracts(data.contracts.filter(r=>[r.reference,r.customer_display,r.unit_label].some(v=>String(v||'').toLocaleLowerCase().includes(q)))));}
function renderLocations() {
 if(!data)return;const q=$('location-search').value.toLowerCase(),kind=$('location-kind').value;
 const list=data.locations.filter(r=>(!kind||r.doctype===kind)&&[r.name,r.label,r.area].some(v=>String(v||'').toLowerCase().includes(q)));
 $('locations').replaceChildren(...(list.length?list.map(r=>el('button',{class:'location-card'+(selectedLocation===r.doctype+':'+r.name?' selected':''),onclick:()=>selectLocation(r)},[el('span',{class:'location-type'},r.doctype==='Sidra Unit'?'Plot / property':'Construction site'),el('span',{class:'pin-state'},r.latitude==null?'Pin not captured':'● Location saved'),el('strong',{},r.label),el('small',{},r.area||r.name)])):[empty('No matching plots or sites.')]));
}
async function selectLocation(item) {
 const scope=data;
 try {if(!preview){const current=await request(config.locationsMethod+'.get_location',{doctype:item.doctype,name:item.name});if(data!==scope)return;Object.assign(item,current);}showLocation(item);}catch(error){message(error.message);}
}
function showLocation(item) {
 selectedLocation=item.doctype+':'+item.name;renderLocations();
 const box=$('location-detail'), hasPoint=item.latitude!=null&&item.longitude!=null;
 const lat=el('input',{type:'number',step:'any',min:'-90',max:'90',value:hasPoint?item.latitude:'',disabled:!item.can_write,required:true,'aria-label':'Latitude'});
 const lng=el('input',{type:'number',step:'any',min:'-180',max:'180',value:hasPoint?item.longitude:'',disabled:!item.can_write,required:true,'aria-label':'Longitude'});
 const status=el('div',{class:'status-message',role:'status'});
 const links=el('div',{class:'location-links'});
 if(hasPoint){const urls=mapLinks(item.latitude,item.longitude);for(const [label,url] of [['Google Maps ↗',urls.maps],['Google Earth ↗',urls.earth]])links.append(el('a',{class:'link-button',href:url,target:'_blank',rel:'noopener noreferrer'},label));if(!preview)links.append(el('a',{class:'link-button',href:'/api/method/'+config.locationsMethod+'.export_kml?'+new URLSearchParams({doctype:item.doctype,name:item.name})},'Download Earth KML'));}
 const visual=el('div',{class:'coordinate-visual','aria-label':hasPoint?'Saved location pin, schematic view':'No location saved'},[hasPoint?el('span',{class:'pin','aria-hidden':'true'}):el('span',{},'No saved pin'),el('small',{},'Coordinate preview · not a basemap')]);
 const content=[el('p',{class:'eyebrow'},item.doctype==='Sidra Unit'?'PLOT LOCATION':'CONSTRUCTION SITE LOCATION'),el('h2',{},item.label),el('p',{class:'coordinate-caption'},item.area||item.name),visual];
 if(hasPoint && config.mapsEmbedKey)content.push(el('iframe',{title:'Google Maps location',loading:'lazy',referrerpolicy:'strict-origin-when-cross-origin',src:`https://www.google.com/maps/embed/v1/place?key=${encodeURIComponent(config.mapsEmbedKey)}&q=${encodeURIComponent(item.latitude+','+item.longitude)}&zoom=17`}));
 content.push(links,el('p',{class:'coordinate-caption'},'The pin is shared with the web and both apps. Surveyed boundaries remain in the source documents.'));
 const save=el('button',{class:'primary-button',type:'submit',disabled:!item.can_write},preview?'Preview pin change':'Save location');
 const gps=el('button',{class:'link-button',type:'button',disabled:!item.can_write,onclick:()=>{
  if(!navigator.geolocation){status.textContent='Device location is unavailable. Enter surveyed coordinates manually.';return;}
  status.textContent='Waiting for location permission…';navigator.geolocation.getCurrentPosition(pos=>{lat.value=pos.coords.latitude;lng.value=pos.coords.longitude;previewPin();status.textContent=`Device accuracy: approximately ${Math.round(pos.coords.accuracy)} m. Review the pin, then save explicitly.`;},()=>{status.textContent='Location was not obtained. You can still enter coordinates manually.';},{enableHighAccuracy:true,timeout:15000,maximumAge:0});
 }},'Use device location');
 const previewPin=()=>{try{const point=coordinates(lat.value,lng.value);const urls=mapLinks(point.latitude,point.longitude);links.replaceChildren(...[['Review in Google Maps ↗',urls.maps],['Review in Google Earth ↗',urls.earth]].map(([label,url])=>el('a',{class:'link-button',href:url,target:'_blank',rel:'noopener noreferrer'},label)));status.textContent='Unsaved coordinates. Review the location, then save explicitly.';}catch(error){status.textContent=error.message;}};
 lat.addEventListener('change',previewPin);lng.addEventListener('change',previewPin);
 const form=el('form',{class:'location-form',onsubmit:async e=>{
  e.preventDefault();save.disabled=true;const scope=data;const selected=selectedLocation;
  try{const point=coordinates(lat.value,lng.value);
   if(preview){Object.assign(item,point);showLocation(item);message('Preview pin updated in memory only. Nothing was saved to a server.');}
   else{const saved=await request(config.locationsMethod+'.set_location',{doctype:item.doctype,name:item.name,...point,expected_modified:item.modified},{write:true});Object.assign(item,saved);if(data===scope && selectedLocation===selected){showLocation(item);message('Location saved to the server.');}}
  }catch(error){status.textContent=error.message;}finally{save.disabled=!item.can_write;}
 }},[el('label',{},'Saved coordinates'),el('div',{class:'coordinate-inputs'},[el('label',{},['Latitude',lat]),el('label',{},['Longitude',lng])]),el('div',{class:'location-actions'},[save,gps]),status]);
 if(!item.can_write)status.textContent='Your server role permits viewing this location only.';
 content.push(form);box.replaceChildren(...content);
}
async function load() {
 const generation=++loadGeneration;
 const company=$('company').value||null, project=$('project').value||null;
 $('evidence-dialog').close();$('evidence-body').replaceChildren();
 aborter?.abort();aborter=new AbortController();$('refresh').disabled=true;$('project').disabled=true;message('');data=null;
 $('connection').textContent='Connecting to server';$('updated').textContent='Awaiting server data';
 for(const id of ['contracts-table','upcoming','locations','sales-metrics','pipeline','payment-metrics','aging','job-metrics','jobs-table']) $(id).replaceChildren();
 $('location-detail').replaceChildren(empty('Loading the selected scope…'));
 renderExecutive(null,{el,empty,preview});
 try {
  let result;
  if(preview){result=structuredClone((await import('./demo.js')).default);$('demo-banner').hidden=false;}
  else result=await request(config.dashboardMethod,{period:$('period').value,company,project},{signal:aborter.signal});
  if(generation!==loadGeneration)return;
  data=requireDashboard(result);selectedLocation=null;$('location-detail').replaceChildren(empty('Select a plot or construction site to view its saved location.'));render();
 }catch(error){
  if(error.name==='AbortError'||generation!==loadGeneration)return;
  data=null;$('signin').hidden=false;$('signout').hidden=true;$('role').textContent='Staff workspace';$('connection').textContent='Server not connected';message(error.message+' Demo preview is available separately at ?demo=1.');
  renderExecutive(null,{el,empty,preview});
 }finally{if(generation===loadGeneration)$('refresh').disabled=false;}
}
$('signout').addEventListener('click',async()=>{try{await request('logout',{}, {write:true});location.assign('/login');}catch(error){message(error.message);}});
$('period').addEventListener('change',()=>{load();if(preview)message('Preview uses one fixed fictional reporting period. The live server applies the selected period.');});
$('refresh').addEventListener('click',load);$('company').addEventListener('change',()=>{$('project').value='';load();});$('project').addEventListener('change',load);$('contract-search').addEventListener('input',renderContracts);$('location-search').addEventListener('input',renderLocations);$('location-kind').addEventListener('change',renderLocations);
$('today').textContent=new Intl.DateTimeFormat('en-GB',{day:'numeric',month:'long',year:'numeric',timeZone:'Africa/Mogadishu'}).format(new Date());
load();
