import { ConfigResponse, RawSchool, School } from '../types'

function toSchool(raw: RawSchool, index: number): School {
  const title = (raw.title ?? raw.name ?? '').trim() || 'Unknown School'
  const descr = (raw.descr ?? raw.description ?? '').trim() || 'No description available.'
  const score = typeof raw.score === 'number' ? raw.score : 0
  const id = String(raw.id ?? title ?? `school-${index}`)

  return {
    id,
    title,
    descr,
    score,
    name: raw.name,
    city: raw.city,
    state: raw.state,
    latitude: raw.latitude,
    longitude: raw.longitude,
    matchScore: raw.matchScore,
    acceptanceRate: raw.acceptanceRate,
    tuition: raw.tuition,
    enrollment: raw.enrollment,
    majors: raw.majors,
    description: raw.description,
    tags: raw.tags,
  }
}

export async function fetchConfig(): Promise<ConfigResponse> {
  const response = await fetch('/api/config')
  if (!response.ok) {
    throw new Error(`Config request failed (${response.status})`)
  }

  return response.json() as Promise<ConfigResponse>
}

export async function fetchSchools(query: string): Promise<School[]> {
  const response = await fetch(`/api/schools?query=${encodeURIComponent(query)}`)
  if (!response.ok) {
    throw new Error(`Search failed (${response.status})`)
  }

  const data = (await response.json()) as RawSchool[]
  return data.map(toSchool)
}
