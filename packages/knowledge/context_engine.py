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
                {
                    "asset_id": candidate.asset_id,
                    "title": candidate.title,
                    "source_uri": candidate.source_uri,
                    "preview": _preview(candidate.content),
                    "relevance": candidate.score,
                    "retrieval_sources": list(candidate.sources),
                }
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
