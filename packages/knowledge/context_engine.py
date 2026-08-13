from dataclasses import dataclass, field
from uuid import uuid4

from packages.knowledge.retrieval import SearchCandidate, merge_candidates


@dataclass(frozen=True)
class PlannedContextPack:
    id: str
    org_id: str
    project_id: str
    level: str
    intent: str
    summary: str
    key_facts: list[dict] = field(default_factory=list)
    source_refs: list[dict] = field(default_factory=list)


@dataclass(frozen=True)
class SourceChunk:
    index: int
    content: str
    source_span: dict[str, int]


class ContextEngine:
    def __init__(self, *, keyword_index, vector_index):
        self.keyword_index = keyword_index
        self.vector_index = vector_index

    def plan_context(
        self,
        *,
        org_id: str,
        project_id: str,
        intent: str,
        query: str,
        token_budget: int = 4000,
    ) -> PlannedContextPack:
        keyword_results = self.keyword_index.search(org_id=org_id, project_id=project_id, query=query)
        vector_results = self.vector_index.search(org_id=org_id, project_id=project_id, query=query)
        candidates = merge_candidates(keyword_results=keyword_results, vector_results=vector_results)
        if not candidates and hasattr(self.keyword_index, "list_assets"):
            candidates = merge_candidates(
                keyword_results=self.keyword_index.list_assets(org_id=org_id, project_id=project_id),
                vector_results=[],
            )
        candidates = _rank_by_intent(candidates, intent=intent)
        summary = self._summarize(candidates, token_budget=token_budget)
        return PlannedContextPack(
            id=uuid4().hex,
            org_id=org_id,
            project_id=project_id,
            level="L1",
            intent=intent,
            summary=summary,
            key_facts=[{"fact": _first_sentence(candidate.content), "source_refs": [candidate.asset_id]} for candidate in candidates[:3]],
            source_refs=[
                _source_ref(candidate, query=query)
                for candidate in candidates
            ],
        )

    def _summarize(self, candidates: list[SearchCandidate], *, token_budget: int) -> str:
        if not candidates:
            return "No relevant project context found."
        max_chars = max(200, token_budget * 4)
        parts = [f"{candidate.title}: {_first_sentence(candidate.content)}" for candidate in candidates[:5]]
        return "\n".join(parts)[:max_chars]


def _first_sentence(content: str) -> str:
    stripped = " ".join(content.strip().split())
    if not stripped:
        return ""
    for separator in (".", "。", "\n"):
        if separator in stripped:
            return stripped.split(separator, 1)[0] + separator
    return stripped


def _preview(content: str, *, max_chars: int = 240) -> str:
    sentence = _first_sentence(content)
    if len(sentence) <= max_chars:
        return sentence
    return sentence[: max_chars - 1].rstrip() + "..."


def _source_ref(candidate: SearchCandidate, *, query: str) -> dict:
    chunk = _best_chunk(candidate.content, query=query)
    return {
        "asset_id": candidate.asset_id,
        "asset_type": candidate.asset_type,
        "chunk_id": _chunk_id(candidate.asset_id, index=chunk.index),
        "title": candidate.title,
        "source_uri": candidate.source_uri,
        "source_span": chunk.source_span,
        "preview": _preview(chunk.content),
        "relevance": candidate.score,
        "retrieval_sources": list(candidate.sources),
    }


def _chunk_id(asset_id: str, *, index: int = 0) -> str:
    return f"{asset_id}:chunk:{index}"


def _best_chunk(content: str, *, query: str) -> SourceChunk:
    chunks = _source_chunks(content)
    if not chunks:
        return SourceChunk(index=0, content="", source_span=_source_span(""))
    query_terms = _terms(query)
    if not query_terms:
        return chunks[0]
    return max(chunks, key=lambda chunk: (_chunk_score(chunk.content, query_terms), -chunk.index))


def _source_chunks(content: str) -> list[SourceChunk]:
    if not content:
        return []
    chunks: list[SourceChunk] = []
    cursor = 0
    for index, paragraph in enumerate(part for part in content.split("\n\n") if part.strip()):
        start_char = content.index(paragraph, cursor)
        end_char = start_char + len(paragraph)
        chunks.append(
            SourceChunk(
                index=index,
                content=paragraph,
                source_span=_source_span(content, start_char=start_char, end_char=end_char),
            )
        )
        cursor = end_char
    return chunks or [SourceChunk(index=0, content=content, source_span=_source_span(content))]


def _source_span(content: str, *, start_char: int = 0, end_char: int | None = None) -> dict[str, int]:
    if end_char is None:
        end_char = len(content)
    if not content:
        return {"start_line": 1, "end_line": 1, "start_char": 0, "end_char": 0}
    start_line = content.count("\n", 0, start_char) + 1
    end_line = content.count("\n", 0, max(start_char, end_char - 1)) + 1
    return {"start_line": start_line, "end_line": end_line, "start_char": start_char, "end_char": end_char}


def _chunk_score(content: str, query_terms: set[str]) -> int:
    haystack_terms = _terms(content)
    return len(query_terms & haystack_terms)


def _terms(text: str) -> set[str]:
    return {term for term in text.lower().replace("_", " ").replace("-", " ").split() if term}


def _rank_by_intent(candidates: list[SearchCandidate], *, intent: str) -> list[SearchCandidate]:
    normalized_intent = intent.lower().replace("-", "_")
    return sorted(
        candidates,
        key=lambda candidate: (candidate.score + _intent_boost(normalized_intent, candidate.asset_type)),
        reverse=True,
    )


def _intent_boost(intent: str, asset_type: str) -> float:
    boosts = {
        "implementation": {"code_file": 2.5, "doc": 0.5, "writeback": -1.5},
        "review": {"writeback": 1.5, "code_file": 1.0, "doc": 0.25},
        "testing": {"code_file": 1.5, "doc": 0.75, "writeback": 0.25},
        "docs": {"doc": 2.0, "project_overview": 1.5, "writeback": 0.5},
        "documentation": {"doc": 2.0, "project_overview": 1.5, "writeback": 0.5},
        "risk": {"writeback": 2.0, "project_overview": 1.0, "doc": 0.75},
        "analysis": {"project_overview": 1.0, "writeback": 0.75, "doc": 0.25},
    }
    return boosts.get(intent, {}).get(asset_type, 0.0)
