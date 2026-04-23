"""
Deterministic, hardcoded semantic filters extracted from natural-language queries.

This module intentionally uses simple rule-based parsing (not an LLM) so that
region/weather preferences are transparent, consistent, and debuggable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


# Centralized region definitions (do not scatter these across the codebase).
REGION_TO_STATES: dict[str, set[str]] = {
    "northeast": {"CT", "ME", "MA", "NH", "RI", "VT", "NJ", "NY", "PA"},
    "south": {"DE", "FL", "GA", "MD", "NC", "SC", "VA", "WV", "AL", "KY", "MS", "TN", "AR", "LA", "OK", "TX"},
    "midwest": {"IL", "IN", "MI", "OH", "WI", "IA", "KS", "MN", "MO", "NE", "ND", "SD"},
    "west": {"AK", "AZ", "CA", "CO", "HI", "ID", "MT", "NV", "NM", "OR", "UT", "WA", "WY"},
}

COAST_TO_STATES: dict[str, set[str]] = {
    "east_coast": {"ME", "NH", "MA", "RI", "CT", "NY", "NJ", "DE", "MD", "VA", "NC", "SC", "GA", "FL"},
    "west_coast": {"CA", "OR", "WA"},
}

# NOTE: These weather rules are heuristic approximations unless real climate data exists.
# We approximate with latitude bands; this is practical for the class project and easy to modify.
LATITUDE_THRESHOLDS = {
    "warm_max_lat": 37.0,      # "warm weather" -> prefer below this latitude
    "cold_min_lat": 40.0,      # "cold weather" -> prefer above this latitude
    "not_too_cold_max_lat": 42.0,  # "not too cold" -> exclude above this latitude
}


@dataclass(frozen=True)
class SemanticFilters:
    # Hard filters
    states_in: frozenset[str] | None = None
    max_latitude: float | None = None
    min_latitude: float | None = None

    # Soft preference (boost, not exclusion). Currently: warm/cold preference.
    prefer_warm: bool = False
    prefer_cold: bool = False

    # For transparency/debugging
    matched_phrases: tuple[str, ...] = ()

    def as_json(self) -> dict:
        return {
            "states_in": sorted(self.states_in) if self.states_in else None,
            "max_latitude": self.max_latitude,
            "min_latitude": self.min_latitude,
            "prefer_warm": self.prefer_warm,
            "prefer_cold": self.prefer_cold,
            "matched_phrases": list(self.matched_phrases),
        }


def _norm_state(state: str | None) -> str | None:
    if not state:
        return None
    s = str(state).strip().upper()
    # Support both "NY" and "New York" style values in DB/seed data.
    if len(s) == 2 and s.isalpha():
        return s
    # If we only have full names, we keep them as-is; the region filters then won't match.
    # (Your dataset appears to store abbreviations; this fallback avoids false positives.)
    return s


def _phrase_in(q: str, phrase: str) -> bool:
    # Simple substring matching is fine here; phrases are explicit and multi-word.
    return phrase in q


def extract_semantic_filters(query: str) -> SemanticFilters:
    q = (query or "").strip().lower()
    if not q:
        return SemanticFilters()

    matched: list[str] = []

    states_in: set[str] | None = None
    max_lat: float | None = None
    min_lat: float | None = None
    prefer_warm = False
    prefer_cold = False

    # Regions
    if any(_phrase_in(q, p) for p in ("in the northeast", "in northeast", "northeastern", "northeast")):
        matched.append("northeast")
        states_in = set(REGION_TO_STATES["northeast"]) if states_in is None else states_in & REGION_TO_STATES["northeast"]
    if any(_phrase_in(q, p) for p in ("in the south", "southern school", "southern", "south")):
        matched.append("south")
        states_in = set(REGION_TO_STATES["south"]) if states_in is None else states_in & REGION_TO_STATES["south"]
    if any(_phrase_in(q, p) for p in ("midwest", "in the midwest", "midwestern")):
        matched.append("midwest")
        states_in = set(REGION_TO_STATES["midwest"]) if states_in is None else states_in & REGION_TO_STATES["midwest"]
    if any(_phrase_in(q, p) for p in ("in the west", "western", "west")):
        # Avoid accidental "west" matches like "northwest" already covered; this is acceptable for the project.
        matched.append("west")
        states_in = set(REGION_TO_STATES["west"]) if states_in is None else states_in & REGION_TO_STATES["west"]

    # Coasts
    if any(_phrase_in(q, p) for p in ("east coast", "on the east coast", "near the ocean on the east coast")):
        matched.append("east_coast")
        states_in = set(COAST_TO_STATES["east_coast"]) if states_in is None else states_in & COAST_TO_STATES["east_coast"]
    if any(_phrase_in(q, p) for p in ("west coast", "on the west coast")):
        matched.append("west_coast")
        states_in = set(COAST_TO_STATES["west_coast"]) if states_in is None else states_in & COAST_TO_STATES["west_coast"]

    # Specific state keywords (minimal, extend as needed)
    if any(_phrase_in(q, p) for p in ("in california", "california")):
        matched.append("california")
        states_in = {"CA"} if states_in is None else states_in & {"CA"}

    # Weather phrases
    if any(_phrase_in(q, p) for p in ("not too cold", "not too chilly", "not freezing")):
        matched.append("not_too_cold")
        # Hard exclusion: remove northernmost schools.
        max_lat = LATITUDE_THRESHOLDS["not_too_cold_max_lat"] if max_lat is None else min(max_lat, LATITUDE_THRESHOLDS["not_too_cold_max_lat"])
    if any(_phrase_in(q, p) for p in ("warm weather", "warm", "sunny")):
        matched.append("warm_weather")
        # Soft preference (boost), not a hard exclusion by default.
        prefer_warm = True
    if any(_phrase_in(q, p) for p in ("cold weather", "cold", "snowy")):
        matched.append("cold_weather")
        prefer_cold = True

    return SemanticFilters(
        states_in=frozenset(states_in) if states_in else None,
        max_latitude=max_lat,
        min_latitude=min_lat,
        prefer_warm=prefer_warm,
        prefer_cold=prefer_cold,
        matched_phrases=tuple(matched),
    )


def school_passes_semantic_filters(
    *,
    school_state: str | None,
    school_latitude: float | None,
    filters: SemanticFilters,
) -> bool:
    if filters.states_in:
        st = _norm_state(school_state)
        if st is None:
            return False
        if st not in filters.states_in:
            return False

    if filters.max_latitude is not None:
        if school_latitude is None:
            return False
        if float(school_latitude) > float(filters.max_latitude):
            return False

    if filters.min_latitude is not None:
        if school_latitude is None:
            return False
        if float(school_latitude) < float(filters.min_latitude):
            return False

    return True


def semantic_preference_boost(
    *,
    school_latitude: float | None,
    filters: SemanticFilters,
) -> float:
    """
    Return a small additive score boost (in cosine-score space) based on soft
    preferences like "warm weather". This does NOT fabricate relevance; it's
    just a tie-breaker for similarly relevant results.
    """
    if school_latitude is None:
        return 0.0

    lat = float(school_latitude)
    boost = 0.0

    if filters.prefer_warm:
        # Prefer lower-latitude schools.
        if lat < LATITUDE_THRESHOLDS["warm_max_lat"]:
            boost += 0.02
        else:
            boost -= 0.005

    if filters.prefer_cold:
        # Prefer higher-latitude schools.
        if lat > LATITUDE_THRESHOLDS["cold_min_lat"]:
            boost += 0.02
        else:
            boost -= 0.005

    return boost

