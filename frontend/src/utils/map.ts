import { LatLngBoundsExpression } from 'leaflet'
import { School } from '../types'

export interface MappableSchool extends School {
  latitude: number;
  longitude: number;
}

export function hasValidCoordinates(school: School): school is MappableSchool {
  return (
    typeof school.latitude === 'number' &&
    Number.isFinite(school.latitude) &&
    typeof school.longitude === 'number' &&
    Number.isFinite(school.longitude) &&
    school.latitude >= -90 &&
    school.latitude <= 90 &&
    school.longitude >= -180 &&
    school.longitude <= 180
  )
}

export function getMappableSchools(schools: School[]): MappableSchool[] {
  return schools.filter(hasValidCoordinates)
}

export function getBoundsForSchools(schools: MappableSchool[]): LatLngBoundsExpression | null {
  if (schools.length === 0) return null
  return schools.map((school) => [school.latitude, school.longitude] as [number, number])
}
