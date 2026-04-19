import { useEffect, useRef } from 'react'
import { School } from '../types'
import SchoolCard from './SchoolCard'

interface SchoolListProps {
  schools: School[];
  selectedSchoolId: string | null;
  hoveredSchoolId: string | null;
  onSelectSchool: (schoolId: string) => void;
  onHoverSchool: (schoolId: string | null) => void;
  onOpenSchoolInfo: (school: School) => void;
}

function SchoolList({
  schools,
  selectedSchoolId,
  hoveredSchoolId,
  onSelectSchool,
  onHoverSchool,
  onOpenSchoolInfo,
}: SchoolListProps): JSX.Element {
  const cardRefs = useRef<Record<string, HTMLDivElement | null>>({})

  useEffect(() => {
    if (!selectedSchoolId) return
    const card = cardRefs.current[selectedSchoolId]
    if (card) {
      card.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  }, [selectedSchoolId, schools])

  return (
    <>
      {schools.map((school) => (
        <SchoolCard
          key={school.id}
          school={school}
          isSelected={selectedSchoolId === school.id}
          isHovered={hoveredSchoolId === school.id}
          onSelect={onSelectSchool}
          onHover={onHoverSchool}
          onOpenInfo={onOpenSchoolInfo}
          cardRef={(element) => {
            cardRefs.current[school.id] = element
          }}
        />
      ))}
    </>
  )
}

export default SchoolList
