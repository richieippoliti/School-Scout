import Chat from '../Chat'
import { School } from '../types'
import MapPane from './MapPane'
import ResultsPanel from './ResultsPanel'
import SearchBar from './SearchBar'

interface SearchPageProps {
  useLlm: boolean;
  query: string;
  schools: School[];
  loading: boolean;
  error: string | null;
  selectedSchoolId: string | null;
  hoveredSchoolId: string | null;
  onQueryChange: (value: string) => void;
  onSubmitSearch: () => void;
  onSelectSchool: (schoolId: string) => void;
  onHoverSchool: (schoolId: string | null) => void;
  onChatSearchTerm: (term: string) => void;
}

function SearchPage({
  useLlm,
  query,
  schools,
  loading,
  error,
  selectedSchoolId,
  hoveredSchoolId,
  onQueryChange,
  onSubmitSearch,
  onSelectSchool,
  onHoverSchool,
  onChatSearchTerm,
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

        <ResultsPanel
          schools={schools}
          loading={loading}
          error={error}
          query={query}
          selectedSchoolId={selectedSchoolId}
          hoveredSchoolId={hoveredSchoolId}
          onSelectSchool={onSelectSchool}
          onHoverSchool={onHoverSchool}
        />

        {useLlm && <Chat onSearchTerm={onChatSearchTerm} />}
      </aside>
    </div>
  )
}

export default SearchPage
