import { useEffect, useMemo } from 'react'
import L from 'leaflet'
import { MapContainer, Marker, Popup, TileLayer, useMap } from 'react-leaflet'
import MarkerClusterGroup from 'react-leaflet-markercluster'
import { School } from '../types'
import { getBoundsForSchools, getMappableSchools } from '../utils/map'
import { formatSchoolLocation } from '../utils/location'

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

function ZoomToSelectedSchool({
  schools,
  selectedSchoolId,
}: {
  schools: School[];
  selectedSchoolId: string | null;
}): null {
  const map = useMap()
  const mappableSchools = useMemo(() => getMappableSchools(schools), [schools])

  useEffect(() => {
    if (!selectedSchoolId) return
    const selected = mappableSchools.find((school) => school.id === selectedSchoolId)
    if (!selected) return
    map.flyTo([selected.latitude, selected.longitude], Math.max(map.getZoom(), 9), { animate: true })
  }, [map, mappableSchools, selectedSchoolId])

  return null
}

function markerIcon(rank: number, selected: boolean, hovered: boolean): L.DivIcon {
  const className = [
    'numbered-marker',
    selected ? 'selected' : '',
    hovered ? 'hovered' : '',
  ]
    .filter(Boolean)
    .join(' ')

  return L.divIcon({
    className,
    html: `<span>${rank}</span>`,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
    popupAnchor: [0, -14],
  })
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
        <ZoomToSelectedSchool schools={schools} selectedSchoolId={selectedSchoolId} />
        <MarkerClusterGroup chunkedLoading maxClusterRadius={40}>
          {mappableSchools.map((school) => {
            const isSelected = school.id === selectedSchoolId
            const isHovered = school.id === hoveredSchoolId
            const rank = school.displayRank ?? 0

            return (
              <Marker
                key={school.id}
                position={[school.latitude, school.longitude]}
                icon={markerIcon(rank, isSelected, isHovered)}
                eventHandlers={{ click: () => onSelectSchool(school.id) }}
              >
                <Popup>
                  <strong>{school.title}</strong>
                  <div>{formatSchoolLocation(school) ?? 'No location text'}</div>
                  <div>Match: {(school.score * 100).toFixed(1)}%</div>
                </Popup>
              </Marker>
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
