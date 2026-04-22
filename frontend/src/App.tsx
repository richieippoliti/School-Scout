import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import './App.css'
import { School, SchoolSearchApiOptions } from './types'
import { fetchConfig, fetchSchools, fetchSchoolsRag } from './api/schools'
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
  const SEARCH_METRIC = 'svd' as const
  const [configLoaded, setConfigLoaded] = useState(false)
  const [ragAvailable, setRagAvailable] = useState(false)
  const [ragEnabled, setRagEnabled] = useState(false)
  const [searchTerm, setSearchTerm] = useState<string>('')
  const [includeNationalUniversities, setIncludeNationalUniversities] = useState(true)
  const [includeLiberalArtsColleges, setIncludeLiberalArtsColleges] = useState(true)
  const [satFilter, setSatFilter] = useState('')
  const [actFilter, setActFilter] = useState('')
  const [gpaFilter, setGpaFilter] = useState('')
  const [gpaOutOfFilter, setGpaOutOfFilter] = useState('')
  const [schools, setSchools] = useState<School[]>([])
  const [llmAnswer, setLlmAnswer] = useState<string | null>(null)
  const [rewrittenQuery, setRewrittenQuery] = useState<string | null>(null)
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
        const available = Boolean(data.llm_available)
        setRagAvailable(available)
        setRagEnabled(available)
        setConfigLoaded(true)
      })
      .catch(() => {
        setRagAvailable(false)
        setRagEnabled(false)
        setConfigLoaded(true)
        setError('Unable to load app configuration.')
      })
  }, [])

  const executeSearch = useCallback(
    async (value: string, apiOptions: SchoolSearchApiOptions): Promise<void> => {
      const trimmedValue = value.trim()
      setError(null)

      if (trimmedValue === '') {
        setSchools([])
        setLlmAnswer(null)
        setRewrittenQuery(null)
        setCurrentPage(1)
        setSelectedSchoolId(null)
        setHoveredSchoolId(null)
        return
      }

      setLoading(true)
      try {
        let nextSchools: School[] = []
        if (ragEnabled) {
          const rag = await fetchSchoolsRag(trimmedValue, SEARCH_METRIC, apiOptions)
          nextSchools = rag.schools
          setLlmAnswer(rag.llmAnswer ?? null)
          setRewrittenQuery(rag.rewrittenQuery ?? null)
        } else {
          nextSchools = await fetchSchools(trimmedValue, SEARCH_METRIC, apiOptions)
          setLlmAnswer(null)
          setRewrittenQuery(null)
        }

        setSchools(nextSchools)
        setCurrentPage(1)
        setSelectedSchoolId(nextSchools[0]?.id ?? null)
        setHoveredSchoolId(null)
      } catch {
        setSchools([])
        setLlmAnswer(null)
        setRewrittenQuery(null)
        setSelectedSchoolId(null)
        setHoveredSchoolId(null)
        setError('Search request failed. Please try again.')
      } finally {
        setLoading(false)
      }
    },
    [ragEnabled],
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

  if (!configLoaded) return <></>

  return (
    <>
      <SearchPage
        query={searchTerm}
        includeNationalUniversities={includeNationalUniversities}
        includeLiberalArtsColleges={includeLiberalArtsColleges}
        ragEnabled={ragEnabled}
        ragAvailable={ragAvailable}
        satFilter={satFilter}
        actFilter={actFilter}
        gpaFilter={gpaFilter}
        gpaOutOfFilter={gpaOutOfFilter}
        schools={currentPageSchools}
        currentPage={currentPage}
        totalPages={totalPages}
        loading={loading}
        error={error}
        llmAnswer={llmAnswer}
        rewrittenQuery={rewrittenQuery}
        selectedSchoolId={selectedSchoolId}
        hoveredSchoolId={hoveredSchoolId}
        onQueryChange={setSearchTerm}
        onSubmitSearch={handleSubmitSearch}
        onIncludeNationalChange={setIncludeNationalUniversities}
        onIncludeLiberalArtsChange={setIncludeLiberalArtsColleges}
        onRagEnabledChange={(value) => {
          // If the backend says LLM is unavailable, keep it disabled.
          if (!ragAvailable) {
            setRagEnabled(false)
            return
          }
          setRagEnabled(value)
        }}
        onSatFilterChange={setSatFilter}
        onActFilterChange={setActFilter}
        onGpaFilterChange={setGpaFilter}
        onGpaOutOfFilterChange={setGpaOutOfFilter}
        onSelectSchool={setSelectedSchoolId}
        onHoverSchool={setHoveredSchoolId}
        onPageChange={handlePageChange}
        onOpenSchoolInfo={setInfoSchool}
      />
      {infoSchool && <SchoolInfoModal school={infoSchool} onClose={() => setInfoSchool(null)} />}
    </>
  )
}

export default App
