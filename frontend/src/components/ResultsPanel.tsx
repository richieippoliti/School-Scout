import { School } from '../types'
import SchoolList from './SchoolList'

interface ResultsPanelProps {
  schools: School[];
  currentPage: number;
  totalPages: number;
  loading: boolean;
  error: string | null;
  query: string;
  selectedSchoolId: string | null;
  hoveredSchoolId: string | null;
  onSelectSchool: (schoolId: string) => void;
  onHoverSchool: (schoolId: string | null) => void;
  onPageChange: (page: number) => void;
  onOpenSchoolInfo: (school: School) => void;
}

function ResultsPanel({
  schools,
  currentPage,
  totalPages,
  loading,
  error,
  query,
  selectedSchoolId,
  hoveredSchoolId,
  onSelectSchool,
  onHoverSchool,
  onPageChange,
  onOpenSchoolInfo,
}: ResultsPanelProps): JSX.Element {
  if (loading) {
    return (
      <div id="answer-box">
        <div className="school-item">
          <p className="school-desc">Searching for schools...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div id="answer-box">
        <div className="school-item">
          <p className="school-desc">{error}</p>
        </div>
      </div>
    )
  }

  if (!query.trim()) {
    return (
      <div id="answer-box">
        <div className="school-item">
          <p className="school-desc">Try a natural language search to get started.</p>
        </div>
      </div>
    )
  }

  if (schools.length === 0) {
    return (
      <div id="answer-box">
        <div className="school-item">
          <p className="school-desc">No schools found. Try broadening your query.</p>
        </div>
      </div>
    )
  }

  return (
    <div id="answer-box">
      <SchoolList
        schools={schools}
        selectedSchoolId={selectedSchoolId}
        hoveredSchoolId={hoveredSchoolId}
        onSelectSchool={onSelectSchool}
        onHoverSchool={onHoverSchool}
        onOpenSchoolInfo={onOpenSchoolInfo}
      />
      {totalPages > 1 && (
        <div className="results-pagination" aria-label="Results pagination">
          <button
            type="button"
            className="pagination-btn"
            onClick={() => onPageChange(currentPage - 1)}
            disabled={currentPage <= 1}
          >
            Previous
          </button>
          <span className="pagination-status">
            Page {currentPage} of {totalPages}
          </span>
          <button
            type="button"
            className="pagination-btn"
            onClick={() => onPageChange(currentPage + 1)}
            disabled={currentPage >= totalPages}
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}

export default ResultsPanel
