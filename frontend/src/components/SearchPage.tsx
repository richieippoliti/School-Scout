import Chat from '../Chat'
import { School, SearchMetric } from '../types'
import MapPane from './MapPane'
import ResultsPanel from './ResultsPanel'
import SearchBar from './SearchBar'

interface SearchPageProps {
  useLlm: boolean;
  query: string;
  searchMetric: SearchMetric;
  schools: School[];
  loading: boolean;
  error: string | null;
  selectedSchoolId: string | null;
  hoveredSchoolId: string | null;
  onQueryChange: (value: string) => void;
  onSubmitSearch: () => void;
  onSearchMetricChange: (metric: SearchMetric) => void;
  onSelectSchool: (schoolId: string) => void;
  onHoverSchool: (schoolId: string | null) => void;
  onChatSearchTerm: (term: string) => void;
}

function SearchPage({
  useLlm,
  query,
  searchMetric,
  schools,
  loading,
  error,
  selectedSchoolId,
  hoveredSchoolId,
  onQueryChange,
  onSubmitSearch,
  onSearchMetricChange,
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

        <div className="results-pane-scroll">
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
        </div>

        <div className="panel-footer metric-footer">
          <label className="metric-label" htmlFor="search-metric">
            Ranking
          </label>
          <select
            id="search-metric"
            className="metric-select"
            value={searchMetric}
            onChange={(e) => {
              onSearchMetricChange(e.target.value as SearchMetric)
            }}
            aria-label="Search ranking metric"
          >
            <option value="tfidf">TF–IDF (cosine)</option>
            <option value="svd">SVD / LSA (TF–IDF + SVD)</option>
          </select>
        </div>

        {useLlm && <Chat onSearchTerm={onChatSearchTerm} />}
      </aside>
    </div>
  )
}

export default SearchPage
