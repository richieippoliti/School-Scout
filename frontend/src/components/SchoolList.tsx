import { School } from '../types'
import SchoolCard from './SchoolCard'

interface SchoolListProps {
  schools: School[];
  selectedSchoolId: string | null;
  hoveredSchoolId: string | null;
  onSelectSchool: (schoolId: string) => void;
  onHoverSchool: (schoolId: string | null) => void;
}

function SchoolList({
  schools,
  selectedSchoolId,
  hoveredSchoolId,
  onSelectSchool,
  onHoverSchool,
}: SchoolListProps): JSX.Element {
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
        />
      ))}
    </>
  )
}

export default SchoolList
