import { useEffect, useMemo } from 'react'
import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from 'react-leaflet'
import MarkerClusterGroup from 'react-leaflet-markercluster'
import { School } from '../types'
import { getBoundsForSchools, getMappableSchools } from '../utils/map'

interface MapPaneProps {
  schools: School[];
  selectedSchoolId: string | null;
  hoveredSchoolId: string | null;
  onSelectSchool: (schoolId: string) => void;
}

function FitMapToResults({ schools }: { schools: School[] }): null {
  const map = useMap()
  const mappableSchools = useMemo(() => getMappableSchools(schools), [schools])

  const bounds = useMemo(() => getBoundsForSchools(mappableSchools), [mappableSchools])

  useEffect(() => {
    if (!bounds) return
    if (mappableSchools.length === 1) {
      const single = mappableSchools[0]
      map.setView([single.latitude, single.longitude], 10, { animate: true })
      return
    }
    map.fitBounds(bounds, { padding: [36, 36], animate: true })
  }, [bounds, map, mappableSchools.length])

  return null
}

function MapPane({ schools, selectedSchoolId, hoveredSchoolId, onSelectSchool }: MapPaneProps): JSX.Element {
  const mappableSchools = useMemo(() => getMappableSchools(schools), [schools])

  return (
    <section className="map-pane" aria-label="School map">
      <MapContainer center={[39.8283, -98.5795]} zoom={4} minZoom={2} maxZoom={14} className="school-map">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FitMapToResults schools={schools} />
        <MarkerClusterGroup chunkedLoading maxClusterRadius={40}>
          {mappableSchools.map((school) => {
            const isSelected = school.id === selectedSchoolId
            const isHovered = school.id === hoveredSchoolId

            return (
              <CircleMarker
                key={school.id}
                center={[school.latitude, school.longitude]}
                pathOptions={{
                  color: isSelected ? '#8C6F00' : '#C9A800',
                  fillColor: isSelected ? '#8C6F00' : '#f4b400',
                  fillOpacity: isHovered ? 0.95 : 0.8,
                  weight: isSelected ? 3 : 2,
                }}
                radius={isSelected ? 10 : isHovered ? 9 : 7}
                eventHandlers={{ click: () => onSelectSchool(school.id) }}
              >
                <Popup>
                  <strong>{school.title}</strong>
                  <div>{school.city && school.state ? `${school.city}, ${school.state}` : 'Location unavailable'}</div>
                  <div>Match: {(school.score * 100).toFixed(1)}%</div>
                </Popup>
              </CircleMarker>
            )
          })}
        </MarkerClusterGroup>
      </MapContainer>
      {mappableSchools.length === 0 && (
        <div className="map-empty-state">
          <p>No valid school coordinates yet. Results still appear in the list.</p>
        </div>
      )}
    </section>
  )
}

export default MapPane
