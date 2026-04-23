export interface SearchFiltersPanelProps {
  ragLlmFeedbackEnabled: boolean
  ragLlmFeedbackAvailable: boolean
  onRagLlmFeedbackChange: (value: boolean) => void
  includeNationalUniversities: boolean
  includeLiberalArtsColleges: boolean
  onIncludeNationalChange: (value: boolean) => void
  onIncludeLiberalArtsChange: (value: boolean) => void
  sat: string
  act: string
  gpa: string
  gpaOutOf: string
  onSatChange: (value: string) => void
  onActChange: (value: string) => void
  onGpaChange: (value: string) => void
  onGpaOutOfChange: (value: string) => void
}

function SearchFiltersPanel({
  ragLlmFeedbackEnabled,
  ragLlmFeedbackAvailable,
  onRagLlmFeedbackChange,
  includeNationalUniversities,
  includeLiberalArtsColleges,
  onIncludeNationalChange,
  onIncludeLiberalArtsChange,
  sat,
  act,
  gpa,
  gpaOutOf,
  onSatChange,
  onActChange,
  onGpaChange,
  onGpaOutOfChange,
}: SearchFiltersPanelProps): JSX.Element {
  return (
    <div className="panel-footer search-filters-footer">
      <details className="filters-disclosure" open>
        <summary className="filters-disclosure-summary">Filters</summary>
        <div className="filters-disclosure-body">
          <fieldset className="filter-field institution-fieldset">
            <legend className="metric-label">RAG</legend>
            <p className="filters-hint" id="rag-llm-hint">
              If enabled, search results include LLM-based query rewriting + a short explanation.
            </p>
            <div className="checkbox-row">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={ragLlmFeedbackEnabled}
                  onChange={(e) => onRagLlmFeedbackChange(e.target.checked)}
                  disabled={!ragLlmFeedbackAvailable}
                  aria-describedby="rag-llm-hint"
                />
                <span>RAG LLM Feedback</span>
              </label>
            </div>
          </fieldset>

          <fieldset className="filter-field institution-fieldset">
            <legend className="metric-label">School types</legend>
            <p className="filters-hint" id="school-types-hint">
              Include results from each dataset (both on by default).
            </p>
            <div className="checkbox-row">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={includeNationalUniversities}
                  onChange={(e) => onIncludeNationalChange(e.target.checked)}
                  aria-describedby="school-types-hint"
                />
                <span>National universities</span>
              </label>
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={includeLiberalArtsColleges}
                  onChange={(e) => onIncludeLiberalArtsChange(e.target.checked)}
                  aria-describedby="school-types-hint"
                />
                <span>Liberal arts colleges</span>
              </label>
            </div>
          </fieldset>

          <fieldset className="filter-field stats-fieldset">
            <legend className="metric-label">Your academics (optional)</legend>
            <p className="filters-hint" id="stats-filters-hint">
              When school-level stats exist in the database, results can be narrowed. Leave blank
              to ignore.
            </p>
            <div className="stats-grid" aria-describedby="stats-filters-hint">
              <label className="stat-input-label">
                SAT (1600)
                <input
                  className="filter-text-input"
                  type="number"
                  inputMode="numeric"
                  min={400}
                  max={1600}
                  step={10}
                  placeholder="e.g. 1420"
                  value={sat}
                  onChange={(e) => onSatChange(e.target.value)}
                  aria-label="SAT score out of 1600"
                />
              </label>
              <label className="stat-input-label">
                ACT (36)
                <input
                  className="filter-text-input"
                  type="number"
                  inputMode="decimal"
                  min={1}
                  max={36}
                  step={1}
                  placeholder="e.g. 32"
                  value={act}
                  onChange={(e) => onActChange(e.target.value)}
                  aria-label="ACT score out of 36"
                />
              </label>
              <div className="gpa-inline">
                <label className="stat-input-label">
                  GPA
                  <input
                    className="filter-text-input"
                    type="number"
                    inputMode="decimal"
                    min={0}
                    max={6}
                    step={0.01}
                    placeholder="3.9"
                    value={gpa}
                    onChange={(e) => onGpaChange(e.target.value)}
                    aria-label="Grade point average score"
                  />
                </label>
                <span className="gpa-slash" aria-hidden="true">
                  /
                </span>
                <label className="stat-input-label gpa-out-of-label">
                  Out of
                  <input
                    className="filter-text-input"
                    type="number"
                    inputMode="decimal"
                    min={1}
                    max={6}
                    step={0.1}
                    placeholder="4.0"
                    value={gpaOutOf}
                    onChange={(e) => onGpaOutOfChange(e.target.value)}
                    aria-label="GPA scale maximum, for example 4.0"
                  />
                </label>
              </div>
            </div>
          </fieldset>
        </div>
      </details>
    </div>
  )
}

export default SearchFiltersPanel
