import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import './App.css'
import { School, SchoolSearchApiOptions } from './types'
import { fetchConfig, fetchSchools, fetchSchoolsWithLLM } from './api/schools'
import SearchPage from './components/SearchPage'
import SchoolInfoModal from './components/SchoolInfoModal'

function buildApiOptions(
  includeNationalUniversities: boolean,
  includeLiberalArtsColleges: boolean,
  satFilter: string,
  actFilter: string,
  gpaFilter: string,
  gpaOutOfFilter: string,
): SchoolSearchApiOptions {
  const satN = satFilter.trim() === '' ? undefined : Number(satFilter)
  const actN = actFilter.trim() === '' ? undefined : Number(actFilter)
  const gpaN = gpaFilter.trim() === '' ? undefined : Number(gpaFilter)
  const gpaOutN = gpaOutOfFilter.trim() === '' ? undefined : Number(gpaOutOfFilter)

  return {
    includeNational: includeNationalUniversities,
    includeLiberalArts: includeLiberalArtsColleges,
    sat: satN != null && Number.isFinite(satN) ? satN : undefined,
    act: actN != null && Number.isFinite(actN) ? actN : undefined,
    gpa: gpaN != null && Number.isFinite(gpaN) ? gpaN : undefined,
    gpaOutOf:
      gpaOutN != null && Number.isFinite(gpaOutN) && gpaOutN > 0 ? gpaOutN : undefined,
  }
}

function App(): JSX.Element {
  const RESULTS_PER_PAGE = 5
  const [ragLlmFeedbackAvailable, setRagLlmFeedbackAvailable] = useState<boolean | null>(null)
  const [ragLlmFeedbackEnabled, setRagLlmFeedbackEnabled] = useState<boolean>(false)
  const [llmSummary, setLlmSummary] = useState<string>('')
  const [extractedQuery, setExtractedQuery] = useState<string>('')
  const ragEnabledRef = useRef(ragLlmFeedbackEnabled)
  ragEnabledRef.current = ragLlmFeedbackEnabled
  const [searchTerm, setSearchTerm] = useState<string>('')
  const [includeNationalUniversities, setIncludeNationalUniversities] = useState(true)
  const [includeLiberalArtsColleges, setIncludeLiberalArtsColleges] = useState(true)
  const [satFilter, setSatFilter] = useState('')
  const [actFilter, setActFilter] = useState('')
  const [gpaFilter, setGpaFilter] = useState('')
  const [gpaOutOfFilter, setGpaOutOfFilter] = useState('')
  const [schools, setSchools] = useState<School[]>([])
  const [currentPage, setCurrentPage] = useState(1)
  const [selectedSchoolId, setSelectedSchoolId] = useState<string | null>(null)
  const [hoveredSchoolId, setHoveredSchoolId] = useState<string | null>(null)
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const [infoSchool, setInfoSchool] = useState<School | null>(null)
  const searchTermRef = useRef(searchTerm)
  searchTermRef.current = searchTerm

  useEffect(() => {
    fetchConfig()
      .then((data) => {
        const available = Boolean(data.use_llm)
        setRagLlmFeedbackAvailable(available)
        setRagLlmFeedbackEnabled(available)
      })
      .catch(() => {
        setRagLlmFeedbackAvailable(false)
        setRagLlmFeedbackEnabled(false)
        setError('Unable to load app configuration.')
      })
  }, [])

  const executeSearch = useCallback(
    async (value: string, apiOptions: SchoolSearchApiOptions): Promise<void> => {
      const trimmedValue = value.trim()
      setError(null)

      if (trimmedValue === '') {
        setSchools([])
        setCurrentPage(1)
        setSelectedSchoolId(null)
        setHoveredSchoolId(null)
        setLlmSummary('')
        setExtractedQuery('')
        return
      }

      setLoading(true)
      try {
        if (ragEnabledRef.current) {
          const result = await fetchSchoolsWithLLM(trimmedValue, apiOptions)
          setSchools(result.schools)
          setLlmSummary(result.llmSummary)
          setExtractedQuery(result.extractedQuery)
          setCurrentPage(1)
          setSelectedSchoolId(result.schools[0]?.id ?? null)
          setHoveredSchoolId(null)
        } else {
          const data = await fetchSchools(trimmedValue, apiOptions)
          setSchools(data)
          setLlmSummary('')
          setExtractedQuery('')
          setCurrentPage(1)
          setSelectedSchoolId(data[0]?.id ?? null)
          setHoveredSchoolId(null)
        }
      } catch {
        setSchools([])
        setSelectedSchoolId(null)
        setHoveredSchoolId(null)
        setError('Search request failed. Please try again.')
      } finally {
        setLoading(false)
      }
    },
    [],
  )

  const handleSubmitSearch = (): void => {
    void executeSearch(
      searchTerm,
      buildApiOptions(
        includeNationalUniversities,
        includeLiberalArtsColleges,
        satFilter,
        actFilter,
        gpaFilter,
        gpaOutOfFilter,
      ),
    )
  }

  const handleRagLlmFeedbackChange = (enabled: boolean): void => {
    if (!ragLlmFeedbackAvailable) return
    setRagLlmFeedbackEnabled(enabled)
    const trimmed = searchTerm.trim()
    if (trimmed !== '') {
      void executeSearch(
        trimmed,
        buildApiOptions(
          includeNationalUniversities,
          includeLiberalArtsColleges,
          satFilter,
          actFilter,
          gpaFilter,
          gpaOutOfFilter,
        ),
      )
    }
  }

  useEffect(() => {
    const trimmed = searchTermRef.current.trim()
    if (trimmed === '') {
      return
    }
    const timerId = window.setTimeout(() => {
      void executeSearch(
        trimmed,
        buildApiOptions(
          includeNationalUniversities,
          includeLiberalArtsColleges,
          satFilter,
          actFilter,
          gpaFilter,
          gpaOutOfFilter,
        ),
      )
    }, 320)
    return () => window.clearTimeout(timerId)
  }, [
    includeNationalUniversities,
    includeLiberalArtsColleges,
    satFilter,
    actFilter,
    gpaFilter,
    gpaOutOfFilter,
    executeSearch,
  ])

  const totalPages = useMemo(
    () => Math.max(1, Math.ceil(schools.length / RESULTS_PER_PAGE)),
    [schools.length],
  )

  useEffect(() => {
    setCurrentPage((prev) => Math.min(prev, totalPages))
  }, [totalPages])

  const currentPageSchools = useMemo(() => {
    const start = (currentPage - 1) * RESULTS_PER_PAGE
    return schools.slice(start, start + RESULTS_PER_PAGE).map((school, index) => ({
      ...school,
      displayRank: start + index + 1,
    }))
  }, [schools, currentPage, RESULTS_PER_PAGE])

  useEffect(() => {
    if (!selectedSchoolId) return
    const isSelectedVisible = currentPageSchools.some((school) => school.id === selectedSchoolId)
    if (!isSelectedVisible && currentPageSchools.length > 0) {
      setSelectedSchoolId(currentPageSchools[0].id)
    }
  }, [selectedSchoolId, currentPageSchools])

  const handlePageChange = (page: number): void => {
    const clamped = Math.min(Math.max(page, 1), totalPages)
    setCurrentPage(clamped)
    const start = (clamped - 1) * RESULTS_PER_PAGE
    const firstSchool = schools[start]
    if (firstSchool) {
      setSelectedSchoolId(firstSchool.id)
    }
  }

  if (ragLlmFeedbackAvailable === null) return <></>

  return (
    <>
      <SearchPage
        useLlm={ragLlmFeedbackEnabled}
        ragLlmFeedbackAvailable={ragLlmFeedbackAvailable}
        ragLlmFeedbackEnabled={ragLlmFeedbackEnabled}
        query={searchTerm}
        includeNationalUniversities={includeNationalUniversities}
        includeLiberalArtsColleges={includeLiberalArtsColleges}
        satFilter={satFilter}
        actFilter={actFilter}
        gpaFilter={gpaFilter}
        gpaOutOfFilter={gpaOutOfFilter}
        schools={currentPageSchools}
        currentPage={currentPage}
        totalPages={totalPages}
        loading={loading}
        error={error}
        selectedSchoolId={selectedSchoolId}
        hoveredSchoolId={hoveredSchoolId}
        onQueryChange={setSearchTerm}
        onSubmitSearch={handleSubmitSearch}
        onRagLlmFeedbackChange={handleRagLlmFeedbackChange}
        onIncludeNationalChange={setIncludeNationalUniversities}
        onIncludeLiberalArtsChange={setIncludeLiberalArtsColleges}
        onSatFilterChange={setSatFilter}
        onActFilterChange={setActFilter}
        onGpaFilterChange={setGpaFilter}
        onGpaOutOfFilterChange={setGpaOutOfFilter}
        onSelectSchool={setSelectedSchoolId}
        onHoverSchool={setHoveredSchoolId}
        onPageChange={handlePageChange}
        onOpenSchoolInfo={setInfoSchool}
        llmSummary={llmSummary}
        extractedQuery={extractedQuery}
      />
      {infoSchool && <SchoolInfoModal school={infoSchool} onClose={() => setInfoSchool(null)} />}
    </>
  )
}

export default App
