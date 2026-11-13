// Read-only access to Frappe's standard REST API on the same origin, using the existing
// session cookie. No tokens are stored anywhere.

export class ApiError extends Error {
  constructor(kind, message, status = 0) {
    super(message)
    this.kind = kind // 'network' | 'denied' | 'server'
    this.status = status
  }
}

export function loginUrl() {
  const back = window.location.pathname + window.location.search
  return '/login?redirect-to=' + encodeURIComponent(back)
}

async function stillSignedIn() {
  try {
    const res = await fetch('/api/method/frappe.auth.get_logged_user', {
      credentials: 'same-origin',
      headers: { Accept: 'application/json' },
    })
    if (!res.ok) return false
    const body = await res.json()
    return Boolean(body.message) && body.message !== 'Guest'
  } catch {
    // Unknown, not "signed out": do not bounce someone to the login page on a network fault.
    return true
  }
}

function serverMessage(body) {
  if (!body || typeof body !== 'object') return ''
  if (Array.isArray(body.errors) && body.errors[0]?.message) return String(body.errors[0].message)
  if (typeof body.exception === 'string') return body.exception.split(':').slice(1).join(':').trim()
  return ''
}

export async function apiGet(path, params = {}) {
  const url = new URL(path, window.location.origin)
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null) continue
    url.searchParams.set(key, typeof value === 'object' ? JSON.stringify(value) : String(value))
  }

  let res
  try {
    res = await fetch(url, { credentials: 'same-origin', headers: { Accept: 'application/json' } })
  } catch {
    throw new ApiError('network', 'The server could not be reached.')
  }

  let body = null
  try {
    body = await res.json()
  } catch {
    body = null
  }

  if (res.status === 401 || res.status === 403) {
    if (!(await stillSignedIn())) {
      window.location.assign(loginUrl())
      // Navigation is under way; keep the caller in its loading state.
      return new Promise(() => {})
    }
    throw new ApiError('denied', serverMessage(body) || 'You do not have access to this.', res.status)
  }
  if (!res.ok || body === null) {
    throw new ApiError(
      'server',
      serverMessage(body) || `The server answered with an error (${res.status}).`,
      res.status,
    )
  }
  return body
}
