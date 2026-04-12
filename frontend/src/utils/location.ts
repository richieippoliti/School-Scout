import { School } from '../types'

/**
 * Short location line for cards/popups. Uses coordinates only (city/state ignored for now).
 */
export function formatSchoolLocation(school: School, coordsDecimals = 2): string | null {
  const lat = school.latitude
  const lng = school.longitude
  if (typeof lat === 'number' && typeof lng === 'number' && Number.isFinite(lat) && Number.isFinite(lng)) {
    return `${lat.toFixed(coordsDecimals)}°, ${lng.toFixed(coordsDecimals)}°`
  }
  return null
}
