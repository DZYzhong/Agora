from dataclasses import dataclass

from packages.domain.schemas import AssetCreate


@dataclass(frozen=True)
class VectorSearchResult:
    asset_id: str
    title: str
    content: str
    source_uri: str
    score: float


class FakeVectorIndex:
    def __init__(self):
        self._assets: list[tuple[str, AssetCreate]] = []

    def index_asset(self, asset_id: str, asset: AssetCreate) -> None:
        self._assets.append((asset_id, asset))

    def search(self, *, org_id: str, project_id: str, query: str, limit: int = 10) -> list[VectorSearchResult]:
        query_terms = _terms(query)
        results: list[VectorSearchResult] = []
        for asset_id, asset in self._assets:
            if asset.org_id != org_id or asset.project_id != project_id:
                continue
            content_terms = _terms(f"{asset.title} {asset.content}")
            overlap = len(query_terms & content_terms)
            if overlap:
                results.append(
                    VectorSearchResult(
                        asset_id=asset_id,
                        title=asset.title,
                        content=asset.content,
                        source_uri=asset.source_uri,
                        score=float(overlap),
                    )
                )
        return sorted(results, key=lambda item: item.score, reverse=True)[:limit]


def _terms(text: str) -> set[str]:
    normalized = _normalize_terms(text)
    return {term for term in normalized.lower().replace("_", " ").replace("-", " ").split() if term}


def _normalize_terms(text: str) -> str:
    replacements = {
        "退款": " refund ",
        "重试": " retry ",
        "幂等": " idempotency ",
        "支付": " payment ",
        "对账": " reconciliation ",
    }
    normalized = text
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)
    return normalized
