export const TYPES = ['Sidra Unit', 'Sidra Construction Job'];
export function serverOrigin(input) {
  const u = new URL(input);
  if (u.protocol !== 'https:' || !u.hostname || u.username || u.password || u.search || u.hash || !['', '/'].includes(u.pathname)) throw new Error('Enter an HTTPS server address, without a path, credentials or query.');
  return u.origin;
}
export function coordinates(latitude, longitude) {
  if ((typeof latitude === 'string' && !latitude.trim()) || (typeof longitude === 'string' && !longitude.trim()) || latitude == null || longitude == null || typeof latitude === 'boolean' || typeof longitude === 'boolean') throw new Error('Enter both latitude and longitude.');
  const lat = Number(latitude), lng = Number(longitude);
  if (!Number.isFinite(lat) || !Number.isFinite(lng) || Math.abs(lat) > 90 || Math.abs(lng) > 180) throw new Error('Latitude must be −90 to 90; longitude must be −180 to 180.');
  return {latitude: lat, longitude: lng};
}
export function mapLinks(latitude, longitude) {
  const {latitude: lat, longitude: lng} = coordinates(latitude, longitude);
  const point = encodeURIComponent(`${lat},${lng}`);
  return {maps: `https://www.google.com/maps/search/?api=1&query=${point}`, earth: `https://earth.google.com/web/search/${point}`};
}
const numericAmount = amount => (typeof amount === 'number' || typeof amount === 'string' && amount.trim() !== '') && Number.isFinite(Number(amount));
export function money(amount, currency = 'USD') {
  if (!numericAmount(amount)) return '—';
  const n = Number(amount);
  return new Intl.NumberFormat('en-GB', {style: 'currency', currency, minimumFractionDigits: 2, maximumFractionDigits: 2}).format(n);
}
export function compactMoney(amount, currency='USD') {
  if (!numericAmount(amount)) return '—';
  return new Intl.NumberFormat('en-GB',{style:'currency',currency,notation:'compact',maximumFractionDigits:1}).format(Number(amount));
}
export function date(value) {
  if (!value) return '—';
  return new Intl.DateTimeFormat('en-GB', {day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC'}).format(new Date(value.length === 10 ? value + 'T00:00:00Z' : value));
}
export function recordPath(doctype, name) {
  const route = {'Sidra Unit': 'sidra-unit', 'Sidra Sale Contract': 'sidra-sale-contract', 'Sidra Construction Job': 'sidra-construction-job'}[doctype];
  if (!route || !name) throw new Error('Unsupported record');
  return `/app/${route}/${encodeURIComponent(name)}`;
}
export function requireDashboard(d) {
  if (!d || d.schema_version !== 1 || !d.scope?.company_name || !Array.isArray(d.companies) || !Array.isArray(d.contracts) || !Array.isArray(d.locations) || !Array.isArray(d.schedule?.buckets) || !Array.isArray(d.schedule?.upcoming) || !Array.isArray(d.property?.counts) || !d.summary || !d.as_of) throw new Error('The server dashboard response is not compatible with this client.');
  return d;
}
export async function request(method, args = {}, {write = false, signal} = {}) {
  if (!/^[a-zA-Z0-9_.]+$/.test(method)) throw new Error('Invalid API method');
  const headers = {Accept: 'application/json'};
  let url = `/api/method/${method}`, body;
  if (write) {
    const csrf = globalThis.frappe?.csrf_token || globalThis.SIDRA_CONFIG?.csrfToken;
    if (!csrf) throw new Error('Reload the server page to obtain a secure session token before saving.');
    headers['Content-Type'] = 'application/json'; headers['X-Frappe-CSRF-Token'] = csrf;
    body = JSON.stringify(args);
  } else url += '?' + new URLSearchParams(Object.entries(args).filter(([, v]) => v != null));
  const r = await fetch(url, {method: write ? 'POST' : 'GET', credentials: 'same-origin', headers, body, signal, cache: 'no-store'});
  if (r.status === 401 || r.status === 403) throw new Error('Sign in with a permitted Sidra staff account, then refresh.');
  if (!r.ok && r.status === 417) {
    const detail=await r.json().catch(()=>({}));
    if(detail.exc_type==='TimestampMismatchError') throw new Error('This record changed. Refresh and reopen its location before saving.');
  }
  if (!r.ok) throw new Error(r.status === 404 ? 'This endpoint is not installed on the server yet.' : `The server could not complete the request (${r.status}).`);
  const payload = await r.json();
  if (payload.exc) throw new Error('The server refused the request. Check your permissions and the record.');
  return payload.message;
}
