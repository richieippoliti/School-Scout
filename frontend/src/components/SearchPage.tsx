import { School, SearchMetric } from '../types'
import MapPane from './MapPane'
import ResultsPanel from './ResultsPanel'
import SearchBar from './SearchBar'
import SearchFiltersPanel from './SearchFiltersPanel'

interface SearchPageProps {
  useLlm: boolean;
  query: string;
  searchMetric: SearchMetric;
  includeNationalUniversities: boolean;
  includeLiberalArtsColleges: boolean;
  satFilter: string;
  actFilter: string;
  gpaFilter: string;
  gpaOutOfFilter: string;
  schools: School[];
  currentPage: number;
  totalPages: number;
  loading: boolean;
  error: string | null;
  selectedSchoolId: string | null;
  hoveredSchoolId: string | null;
  onQueryChange: (value: string) => void;
  onSubmitSearch: () => void;
  onSearchMetricChange: (metric: SearchMetric) => void;
  onIncludeNationalChange: (value: boolean) => void;
  onIncludeLiberalArtsChange: (value: boolean) => void;
  onSatFilterChange: (value: string) => void;
  onActFilterChange: (value: string) => void;
  onGpaFilterChange: (value: string) => void;
  onGpaOutOfFilterChange: (value: string) => void;
  onSelectSchool: (schoolId: string) => void;
  onHoverSchool: (schoolId: string | null) => void;
  onPageChange: (page: number) => void;
  onOpenSchoolInfo: (school: School) => void;
  llmSummary: string;
  extractedQuery: string;
}

function SearchPage({
  useLlm,
  query,
  searchMetric,
  includeNationalUniversities,
  includeLiberalArtsColleges,
  satFilter,
  actFilter,
  gpaFilter,
  gpaOutOfFilter,
  schools,
  currentPage,
  totalPages,
  loading,
  error,
  selectedSchoolId,
  hoveredSchoolId,
  onQueryChange,
  onSubmitSearch,
  onSearchMetricChange,
  onIncludeNationalChange,
  onIncludeLiberalArtsChange,
  onSatFilterChange,
  onActFilterChange,
  onGpaFilterChange,
  onGpaOutOfFilterChange,
  onSelectSchool,
  onHoverSchool,
  onPageChange,
  onOpenSchoolInfo,
  llmSummary,
  extractedQuery,
}: SearchPageProps): JSX.Element {
  return (
    <div className={`search-layout ${useLlm ? 'llm-mode' : ''}`}>
      <MapPane
        schools={schools}
        selectedSchoolId={selectedSchoolId}
        hoveredSchoolId={hoveredSchoolId}
        onSelectSchool={onSelectSchool}
      />
      <aside className="results-pane" aria-label="Search and results panel">
        <div className="panel-sticky-top">
          <div className="brand-title">
            <span className="brand-cap">🎓</span>
            <h1 className="brand-name">SchoolScout</h1>
          </div>
          <p className="brand-subtitle">Find your perfect college match</p>
          <SearchBar
            value={query}
            onChange={onQueryChange}
            onSubmit={onSubmitSearch}
            loading={loading}
          />
        </div>

        <div className="results-pane-scroll">
          <ResultsPanel
            schools={schools}
            currentPage={currentPage}
            totalPages={totalPages}
            loading={loading}
            error={error}
            query={query}
            selectedSchoolId={selectedSchoolId}
            hoveredSchoolId={hoveredSchoolId}
            onSelectSchool={onSelectSchool}
            onHoverSchool={onHoverSchool}
            onPageChange={onPageChange}
            onOpenSchoolInfo={onOpenSchoolInfo}
          />
        </div>

        <SearchFiltersPanel
          searchMetric={searchMetric}
          onSearchMetricChange={onSearchMetricChange}
          includeNationalUniversities={includeNationalUniversities}
          includeLiberalArtsColleges={includeLiberalArtsColleges}
          onIncludeNationalChange={onIncludeNationalChange}
          onIncludeLiberalArtsChange={onIncludeLiberalArtsChange}
          sat={satFilter}
          act={actFilter}
          gpa={gpaFilter}
          gpaOutOf={gpaOutOfFilter}
          onSatChange={onSatFilterChange}
          onActChange={onActFilterChange}
          onGpaChange={onGpaFilterChange}
          onGpaOutOfChange={onGpaOutOfFilterChange}
        />

        {useLlm && llmSummary && (
          <div className="llm-summary-banner">
            <span className="llm-summary-icon">🤖</span>
            <div className="llm-summary-body">
              <p className="llm-summary-text">{llmSummary}</p>
              {extractedQuery && (
                <p className="llm-extracted-query">Searched for: <em>{extractedQuery}</em></p>
              )}
            </div>
          </div>
        )}
      </aside>
    </div>
  )
}

export default SearchPage
