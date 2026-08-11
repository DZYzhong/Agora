from sqlalchemy.orm import Session

from packages.core.repositories.assets import AssetRepository
from packages.domain.schemas import AssetCreate


def rebuild_indexes_from_assets(session: Session, keyword_index, vector_index) -> int:
    asset_count = 0
    for asset in AssetRepository(session).list_all():
        payload = AssetCreate(
            org_id=asset.org_id,
            project_id=asset.project_id,
            type=asset.type,
            source=asset.source,
            source_uri=asset.source_uri,
            title=asset.title,
            content=asset.content,
            summary=asset.summary,
            metadata=asset.asset_metadata,
            content_hash=asset.content_hash,
        )
        keyword_index.index_asset(asset.id, payload)
        vector_index.index_asset(asset.id, payload)
        asset_count += 1
    return asset_count
