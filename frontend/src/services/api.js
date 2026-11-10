const API_BASE_URL = '/api/v1'

async function apiRequest(endpoint) {
  const response = await fetch(`${API_BASE_URL}${endpoint}`)

  if (!response.ok) {
    throw new Error(
      `Erreur API ${response.status}: ${response.statusText}`
    )
  }

  return response.json()
}

export const getOverview = (params = {}) => {
  const query = new URLSearchParams(params)
  return apiRequest(`/analytics/overview/?${query}`)
}

export const getTimeline = (params = {}) => {
  const query = new URLSearchParams(params)
  return apiRequest(`/analytics/timeline/?${query}`)
}

export const getMaritimeCells = (params = {}) => {
  const query = new URLSearchParams(params)
  return apiRequest(`/analytics/map/?${query}`)
}

export const getMaritimeZone = () => {
  return apiRequest('/analytics/zone/')
}



export const getRanking = (params = {}) => {
  const query = new URLSearchParams(params)
  return apiRequest(`/analytics/ranking/?${query}`)
}
export const getTemporal = (params = {}) => {
  const query = new URLSearchParams(params)
  return apiRequest(`/analytics/temporal/?${query}`)
}