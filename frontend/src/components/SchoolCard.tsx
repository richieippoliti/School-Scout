import { School } from '../types'

interface SchoolCardProps {
  school: School;
  isSelected: boolean;
  isHovered: boolean;
  onSelect: (schoolId: string) => void;
  onHover: (schoolId: string | null) => void;
}

function SchoolCard({ school, isSelected, isHovered, onSelect, onHover }: SchoolCardProps): JSX.Element {
  const location =
    school.city && school.state ? `${school.city}, ${school.state}` : school.city ?? school.state ?? null

  return (
    <button
      type="button"
      className={`school-item ${isSelected ? 'selected' : ''} ${isHovered ? 'hovered' : ''}`}
      onClick={() => onSelect(school.id)}
      onMouseEnter={() => onHover(school.id)}
      onMouseLeave={() => onHover(null)}
      onFocus={() => onHover(school.id)}
      onBlur={() => onHover(null)}
      aria-pressed={isSelected}
    >
      <h3 className="school-title">{school.title}</h3>
      {location && <p className="school-location">{location}</p>}
      <p className="school-desc">{school.descr}</p>
      <p className="school-score">Match Score: {(school.score * 100).toFixed(1)}%</p>
    </button>
  )
}

export default SchoolCard
