import { useState, useEffect } from 'react'
import './App.css'
import { School, SearchMetric } from './types'
import { fetchConfig, fetchSchools } from './api/schools'
import SearchPage from './components/SearchPage'

function App(): JSX.Element {
  const [useLlm, setUseLlm] = useState<boolean | null>(null)
  const [searchTerm, setSearchTerm] = useState<string>('')
  const [searchMetric, setSearchMetric] = useState<SearchMetric>('tfidf')
  const [schools, setSchools] = useState<School[]>([])
  const [selectedSchoolId, setSelectedSchoolId] = useState<string | null>(null)
  const [hoveredSchoolId, setHoveredSchoolId] = useState<string | null>(null)
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchConfig()
      .then((data) => setUseLlm(data.use_llm))
      .catch(() => {
        setUseLlm(false)
        setError('Unable to load app configuration.')
      })
  }, [])

  const executeSearch = async (value: string, metric: SearchMetric): Promise<void> => {
    const trimmedValue = value.trim()
    setError(null)

    if (trimmedValue === '') {
      setSchools([])
      setSelectedSchoolId(null)
      setHoveredSchoolId(null)
      return
    }

    setLoading(true)
    try {
      const data = await fetchSchools(trimmedValue, metric)
      setSchools(data)
      setSelectedSchoolId(data[0]?.id ?? null)
      setHoveredSchoolId(null)
    } catch {
      setSchools([])
      setSelectedSchoolId(null)
      setHoveredSchoolId(null)
      setError('Search request failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmitSearch = (): void => {
    void executeSearch(searchTerm, searchMetric)
  }

  const handleSearchMetricChange = (metric: SearchMetric): void => {
    setSearchMetric(metric)
    const trimmed = searchTerm.trim()
    if (trimmed !== '') {
      void executeSearch(trimmed, metric)
    }
  }

  const handleChatSearchTerm = (term: string): void => {
    setSearchTerm(term)
    void executeSearch(term, searchMetric)
  }

  if (useLlm === null) return <></>

  return (
    <SearchPage
      useLlm={useLlm}
      query={searchTerm}
      searchMetric={searchMetric}
      schools={schools}
      loading={loading}
      error={error}
      selectedSchoolId={selectedSchoolId}
      hoveredSchoolId={hoveredSchoolId}
      onQueryChange={setSearchTerm}
      onSubmitSearch={handleSubmitSearch}
      onSearchMetricChange={handleSearchMetricChange}
      onSelectSchool={setSelectedSchoolId}
      onHoverSchool={setHoveredSchoolId}
      onChatSearchTerm={handleChatSearchTerm}
    />
  )
}

export default App
