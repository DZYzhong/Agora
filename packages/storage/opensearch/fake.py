from dataclasses import dataclass

from packages.domain.schemas import AssetCreate


@dataclass(frozen=True)
class KeywordSearchResult:
    asset_id: str
    title: str
    content: str
    source_uri: str
    score: float


class FakeKeywordIndex:
    def __init__(self):
        self._assets: list[tuple[str, AssetCreate]] = []

    def index_asset(self, asset_id: str, asset: AssetCreate) -> None:
        self._assets.append((asset_id, asset))

    def list_assets(self, *, org_id: str, project_id: str, limit: int = 20) -> list[KeywordSearchResult]:
        project_assets = [
            (asset_id, asset)
            for asset_id, asset in self._assets
            if asset.org_id == org_id and asset.project_id == project_id
        ]
        project_assets = sorted(project_assets, key=lambda item: 0 if item[1].type == "project_overview" else 1)
        results = [
            KeywordSearchResult(
                asset_id=asset_id,
                title=asset.title,
                content=asset.content,
                source_uri=asset.source_uri,
                score=1.0 if asset.type == "project_overview" else 0.1,
            )
            for asset_id, asset in project_assets
        ]
        return results[:limit]

    def search(self, *, org_id: str, project_id: str, query: str, limit: int = 10) -> list[KeywordSearchResult]:
        query_lower = _normalize_terms(query).lower()
        results: list[KeywordSearchResult] = []
        for asset_id, asset in self._assets:
            if asset.org_id != org_id or asset.project_id != project_id:
                continue
            haystack = f"{asset.title}\n{asset.content}".lower()
            score = sum(1 for token in query_lower.split() if token in haystack)
            if score:
                results.append(
                    KeywordSearchResult(
                        asset_id=asset_id,
                        title=asset.title,
                        content=asset.content,
                        source_uri=asset.source_uri,
                        score=float(score) + _asset_score_boost(asset.type),
                    )
                )
        return sorted(results, key=lambda item: item.score, reverse=True)[:limit]


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


def _asset_score_boost(asset_type: str) -> float:
    if asset_type == "writeback":
        return 2.0
    if asset_type == "project_overview":
        return 0.5
    return 0.0
