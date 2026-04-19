import { ConfigResponse, RawSchool, School, SchoolSearchApiOptions, SearchMetric } from '../types'

function finiteNumber(value: unknown): number | undefined {
  if (value == null || value === '') return undefined
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string') {
    const n = Number(value.trim())
    return Number.isFinite(n) ? n : undefined
  }
  return undefined
}

function optionalString(value: unknown): string | undefined {
  if (value == null) return undefined
  const s = String(value).trim()
  return s || undefined
}

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
    name: optionalString(raw.name),
    latitude: finiteNumber(raw.latitude),
    longitude: finiteNumber(raw.longitude),
    matchScore: finiteNumber(raw.matchScore),
    acceptanceRate: finiteNumber(raw.acceptanceRate ?? raw.acceptance_rate),
    tuition: finiteNumber(raw.tuition),
    enrollment: finiteNumber(raw.enrollment),
    majors: raw.majors,
    description: raw.description,
    tags: raw.tags,
    institutionType: optionalString(raw.institutionType),
    nicheUrl: optionalString(raw.nicheUrl),
    reviews: Array.isArray(raw.reviews) ? raw.reviews : undefined,
    matchingChunks: Array.isArray(raw.matchingChunks) ? raw.matchingChunks : undefined,
    queryTerms: Array.isArray(raw.queryTerms) ? raw.queryTerms : undefined,
  }
}

export async function fetchConfig(): Promise<ConfigResponse> {
  const response = await fetch('/api/config')
  if (!response.ok) {
    throw new Error(`Config request failed (${response.status})`)
  }

  return response.json() as Promise<ConfigResponse>
}

export async function fetchSchools(
  query: string,
  metric: SearchMetric = 'tfidf',
  options: SchoolSearchApiOptions = {},
): Promise<School[]> {
  const params = new URLSearchParams({ query, metric })
  if (options.includeNational === false) {
    params.set('include_national', '0')
  } else {
    params.set('include_national', '1')
  }
  if (options.includeLiberalArts === false) {
    params.set('include_liberal_arts', '0')
  } else {
    params.set('include_liberal_arts', '1')
  }
  if (options.sat != null && Number.isFinite(options.sat)) {
    params.set('sat', String(Math.round(options.sat)))
  }
  if (options.act != null && Number.isFinite(options.act)) {
    params.set('act', String(options.act))
  }
  if (options.gpa != null && Number.isFinite(options.gpa)) {
    params.set('gpa', String(options.gpa))
  }
  if (options.gpaOutOf != null && Number.isFinite(options.gpaOutOf) && options.gpaOutOf > 0) {
    params.set('gpa_out_of', String(options.gpaOutOf))
  }
  const response = await fetch(`/api/schools?${params.toString()}`)
  if (!response.ok) {
    throw new Error(`Search failed (${response.status})`)
  }

  const data = (await response.json()) as RawSchool[]
  return data.map(toSchool)
}
