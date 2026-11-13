import { apiGet } from './api.js'
export const TIMELINE_METHOD = 'sidra_realestate.api.workflow.get_contract_timeline'
export const CONTRACT = '/api/resource/' + encodeURIComponent('Sidra Sale Contract')
export const textValue = value => value === null || value === undefined || value === '' || value === 'unavailable' ? 'Unavailable' : String(value)
export const statusText = value => ({ 0: 'Draft', 1: 'Confirmed', 2: 'Cancelled' })[value] || 'Unavailable'
export const numeric = value => typeof value === 'number' && Number.isFinite(value)
export function money(value, currency) {
  return numeric(value) ? `${currency || ''} ${value.toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`.trim() : 'Unavailable'
}
export function fileLink(value) {
  return typeof value === 'string' && /^\/(private\/)?files\/[^\s]+$/.test(value) && !value.includes('\\') ? value : null
}
export function recordLink(record) {
  return record?.doctype && record?.name ? `/app/${encodeURIComponent(record.doctype.toLowerCase().replaceAll(' ', '-'))}/${encodeURIComponent(record.name)}` : null
}
export async function timeline(name) {
  const response = await apiGet('/api/method/' + TIMELINE_METHOD, { contract: name })
  if (!response.message || !Array.isArray(response.message.stages)) throw new Error('Unexpected workflow response.')
  return response.message
}
