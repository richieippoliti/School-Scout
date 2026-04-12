/** Retrieval / ranking metric: raw TF-IDF cosine, or LSA (TF-IDF + truncated SVD). */
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
}
