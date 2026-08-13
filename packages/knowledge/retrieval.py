from dataclasses import dataclass
from typing import Protocol


class RawSearchResult(Protocol):
    asset_id: str
    asset_type: str
    title: str
    content: str
    source_uri: str
    score: float


@dataclass(frozen=True)
class SearchCandidate:
    asset_id: str
    asset_type: str
    title: str
    content: str
    source_uri: str
    score: float
    sources: tuple[str, ...]


def merge_candidates(
    *,
    keyword_results: list[RawSearchResult],
    vector_results: list[RawSearchResult],
    limit: int = 10,
) -> list[SearchCandidate]:
    merged: dict[str, SearchCandidate] = {}
    _merge_into(merged, keyword_results, "keyword")
    _merge_into(merged, vector_results, "vector")
    return sorted(merged.values(), key=lambda item: item.score, reverse=True)[:limit]


def _merge_into(merged: dict[str, SearchCandidate], results: list[RawSearchResult], source: str) -> None:
    for result in results:
        existing = merged.get(result.asset_id)
        if existing is None:
            merged[result.asset_id] = SearchCandidate(
                asset_id=result.asset_id,
                asset_type=result.asset_type,
                title=result.title,
                content=result.content,
                source_uri=result.source_uri,
                score=result.score,
                sources=(source,),
            )
            continue
        merged[result.asset_id] = SearchCandidate(
            asset_id=existing.asset_id,
            asset_type=existing.asset_type,
            title=existing.title,
            content=existing.content,
            source_uri=existing.source_uri,
            score=max(existing.score, result.score) + 0.25,
            sources=tuple(sorted(set(existing.sources + (source,)))),
        )
