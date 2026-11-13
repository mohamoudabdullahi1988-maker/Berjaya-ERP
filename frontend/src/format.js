// Display helpers shared by every page. They only format what the server sent: a value the
// server withheld or did not record is shown as "Unavailable" or a dash, never as zero.

export const UNAVAILABLE = 'Unavailable'

export function isMissing(value) {
  return value === null || value === undefined || value === '' || value === 'unavailable'
}

export function textValue(value) {
  return isMissing(value) ? UNAVAILABLE : String(value)
}

/** A number, or an exact decimal string as the server's money() helpers send ("1234.50"). */
export function isAmount(value) {
  if (typeof value === 'number') return Number.isFinite(value)
  return typeof value === 'string' && /^-?\d+(\.\d+)?$/.test(value)
}

function group(digits) {
  return digits.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
}

/** "USD 9,200.00", or "Unavailable". Decimal strings are grouped as text, never re-rounded. */
export function money(value, currency) {
  if (!isAmount(value)) return UNAVAILABLE
  const fixed = typeof value === 'number' ? value.toFixed(2) : value
  const negative = fixed.startsWith('-')
  const [whole, fraction = ''] = fixed.replace('-', '').split('.')
  const amount = `${negative ? '-' : ''}${group(whole)}.${(fraction + '00').slice(0, 2)}`
  return currency ? `${currency} ${amount}` : amount
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

/** "14 Nov 2026" from a server date or datetime; the text is not passed through a time zone. */
export function dateText(value) {
  const match = typeof value === 'string' && /^(\d{4})-(\d{2})-(\d{2})/.exec(value)
  if (!match) return isMissing(value) ? '—' : String(value)
  return `${Number(match[3])} ${MONTHS[Number(match[2]) - 1]} ${match[1]}`
}

/** "14 Nov 2026, 21:37" from a server datetime. */
export function dateTimeText(value) {
  const match = typeof value === 'string' && /^\d{4}-\d{2}-\d{2}[ T](\d{2}:\d{2})/.exec(value)
  return match ? `${dateText(value)}, ${match[1]}` : dateText(value)
}

export function monthText(month) {
  const match = /^(\d{4})-(\d{2})$/.exec(month || '')
  return match ? `${MONTHS[Number(match[2]) - 1]} ${match[1]}` : String(month)
}

/** Month arithmetic on "YYYY-MM". */
export function shiftMonth(month, by) {
  const [year, index] = month.split('-').map(Number)
  const total = year * 12 + (index - 1) + by
  return `${Math.floor(total / 12)}-${String((total % 12) + 1).padStart(2, '0')}`
}

export function percentText(value) {
  return typeof value === 'number' && Number.isFinite(value) ? `${Math.round(value * 10) / 10}%` : UNAVAILABLE
}

/** A link to a file only when it is one of this site's own file paths. */
export function fileLink(value) {
  return typeof value === 'string' && /^\/(private\/)?files\/[^\s]+$/.test(value) && !value.includes('\\') ? value : null
}

/** The Desk form of a record, for "open the supporting record" links. */
export function recordLink(record) {
  return record?.doctype && record?.name
    ? `/app/${encodeURIComponent(record.doctype.toLowerCase().replaceAll(' ', '-'))}/${encodeURIComponent(record.name)}`
    : null
}

/** Only this site's own relative paths are followed (server-supplied drill-down links). */
export function sitePath(value) {
  return typeof value === 'string' && /^\/(?!\/)[^\s\\]*$/.test(value) ? value : null
}
