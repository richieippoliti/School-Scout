/** Retrieval / ranking metric: raw TF-IDF cosine, or SVD with Sentiment Analysis (TF-IDF + truncated SVD). */
export type SearchMetric = 'tfidf' | 'svd';

export interface School {
  id: string;
  title: string;
  descr: string;
  score: number;
  name?: string;
  city?: string;
  state?: string;
  latitude?: number;
  longitude?: number;
  matchScore?: number;
  acceptanceRate?: number;
  tuition?: number;
  enrollment?: number;
  majors?: string[];
  description?: string;
  tags?: string[];
  /** national_university | liberal_arts when provided by API */
  institutionType?: string;
  matchingChunks?: string[];
  queryTerms?: string[];
  displayRank?: number;
  nicheUrl?: string;
  reviews?: SchoolReview[];
}

export interface SchoolReview {
  text?: string;
  rating?: number;
  date?: string;
  reviewer_type?: string;
}

/** Optional query parameters for /api/schools */
export interface SchoolSearchApiOptions {
  includeNational?: boolean;
  includeLiberalArts?: boolean;
  sat?: number;
  act?: number;
  gpa?: number;
  gpaOutOf?: number;
}

export interface SearchFilters {
  major?: string;
  region?: string;
  size?: string;
  tuition?: string;
  selectivity?: string;
  locale?: string;
}

export interface SearchState {
  query: string;
  filters: SearchFilters;
  results: School[];
  selectedSchoolId: string | null;
  hoveredSchoolId: string | null;
  loading: boolean;
  error: string | null;
}

export interface ConfigResponse {
  use_llm: boolean;
}

export interface LLMSearchResult {
  schools: School[];
  extractedQuery: string;
  llmSummary: string;
}

export interface RawSchool {
  id?: string | number;
  title?: string;
  descr?: string;
  score?: number;
  name?: string;
  city?: string | null;
  state?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  matchScore?: number;
  acceptanceRate?: number | null;
  acceptance_rate?: number | null;
  tuition?: number | null;
  enrollment?: number | null;
  majors?: string[];
  description?: string;
  tags?: string[];
  institutionType?: string;
  matchingChunks?: string[];
  queryTerms?: string[];
  nicheUrl?: string;
  reviews?: SchoolReview[];
}
