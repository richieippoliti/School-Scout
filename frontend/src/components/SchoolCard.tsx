import { School } from '../types'
import { formatSchoolLocation } from '../utils/location'

interface SchoolCardProps {
  school: School;
  isSelected: boolean;
  isHovered: boolean;
  onSelect: (schoolId: string) => void;
  onHover: (schoolId: string | null) => void;
}

function highlightTerms(text: string, terms: string[]): React.ReactNode[] {
  if (!terms.length) return [text]
  const escaped = terms.map(t => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
  const pattern= new RegExp(`(${escaped.join('|')})`, 'gi')
  const parts = text.split(pattern)
  return parts.map((part, i) =>
    terms.some(t => t.toLowerCase() === part.toLowerCase())
      ? <strong key={i} className="chunk-highlight">{part}</strong>
      : part
  )
}

function SchoolCard({ school, isSelected, isHovered, onSelect, onHover }: SchoolCardProps): JSX.Element {
  const location = formatSchoolLocation(school)
  const chunks =school.matchingChunks ?? []
  const terms = school.queryTerms ?? []

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
      {terms.length > 0 && (
        <p className="school-matched-terms">
          Matched: {terms.join(', ')}
        </p>
      )}
      {chunks.length > 0 && (
        <div className="school-chunks">
          {chunks.map((chunk, i) => (
            <p key={i} className="school-chunk">"{highlightTerms(chunk, terms)}"</p>
          ))}
        </div>
      )}
      <p className="school-score">Match Score: {(school.score * 100).toFixed(1)}%</p>
    </button>
  )
}

export default SchoolCard
