export const numeric = value => (typeof value === 'number' || typeof value === 'string' && value.trim() !== '') && Number.isFinite(Number(value))
export function format(value, kind, currency) {
  if (!numeric(value)) return 'Unavailable'
  const amount = new Intl.NumberFormat('en-GB', { maximumFractionDigits: kind === 'money' ? 2 : 1 }).format(Number(value))
  return kind === 'money' ? `${currency || ''} ${amount}`.trim() : amount
}
