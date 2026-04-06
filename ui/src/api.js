const API_BASE = '/api'

async function request(path, options = {}, timeoutMs = 600_000) {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs)

  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
    })

    if (!response.ok) {
      const detail = await response.text()
      throw new Error(`HTTP ${response.status}: ${detail}`)
    }

    if (response.status === 204) {
      return null
    }

    return await response.json()
  } catch (err) {
    if (err.name === 'AbortError') {
      throw new Error('Request timed out. Please retry.')
    }
    throw err
  } finally {
    clearTimeout(timeoutId)
  }
}

export function checkHealth() {
  return request('/health', { method: 'GET', headers: {} }, 20_000)
}

export function listConversations() {
  return request('/conversations', { method: 'GET', headers: {} }, 20_000)
}

export function getConversation(sessionId) {
  return request(`/conversations/${sessionId}`, { method: 'GET', headers: {} }, 20_000)
}

export function deleteConversation(sessionId) {
  return request(`/conversations/${sessionId}`, { method: 'DELETE', headers: {} }, 20_000)
}

export function startDesignAsync(prompt, preferredLanguage = 'Python', diagramStyle = 'balanced') {
  return request('/design/async', {
    method: 'POST',
    body: JSON.stringify({
      input: prompt,
      preferred_language: preferredLanguage,
      diagram_style: diagramStyle,
    }),
  })
}

export function startFollowUpAsync(
  sessionId,
  message,
  preferredLanguage = 'Python',
  diagramStyle = 'balanced',
  preserveCoreDiagram = true,
) {
  return request('/design/followup/async', {
    method: 'POST',
    body: JSON.stringify({
      session_id: sessionId,
      message,
      preferred_language: preferredLanguage,
      diagram_style: diagramStyle,
      preserve_core_diagram: preserveCoreDiagram,
    }),
  })
}

export function getOperationStatus(operationId) {
  return request(`/operations/${operationId}`, { method: 'GET', headers: {} }, 20_000)
}
