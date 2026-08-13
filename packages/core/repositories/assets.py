from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.core.models import AssetModel


class AssetRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        *,
        org_id: str,
        project_id: str,
        type: str,
        source: str,
        source_uri: str,
        title: str,
        content: str,
        summary: str | None = None,
        metadata: dict | None = None,
        content_hash: str | None = None,
    ) -> AssetModel:
        asset = AssetModel(
            org_id=org_id,
            project_id=project_id,
            type=type,
            source=source,
            source_uri=source_uri,
            title=title,
            content=content,
            summary=summary,
            asset_metadata=metadata or {},
            content_hash=content_hash,
        )
        self.session.add(asset)
        self.session.commit()
        self.session.refresh(asset)
        return asset

    def get(self, asset_id: str) -> AssetModel | None:
        return self.session.get(AssetModel, asset_id)

    def list_by_project(self, project_id: str) -> list[AssetModel]:
        statement = select(AssetModel).where(AssetModel.project_id == project_id)
        return list(self.session.scalars(statement).all())

    def list_all(self) -> list[AssetModel]:
        return list(self.session.scalars(select(AssetModel)).all())

    def find_by_project_source_uri(self, *, project_id: str, source_uri: str) -> AssetModel | None:
        statement = select(AssetModel).where(
            AssetModel.project_id == project_id,
            AssetModel.source_uri == source_uri,
        )
        return self.session.scalars(statement).first()

    def upsert_by_source_uri(
        self,
        *,
        org_id: str,
        project_id: str,
        type: str,
        source: str,
        source_uri: str,
        title: str,
        content: str,
        summary: str | None = None,
        metadata: dict | None = None,
        content_hash: str | None = None,
    ) -> AssetModel:
        asset = self.find_by_project_source_uri(project_id=project_id, source_uri=source_uri)
        if asset is None:
            return self.create(
                org_id=org_id,
                project_id=project_id,
                type=type,
                source=source,
                source_uri=source_uri,
                title=title,
                content=content,
                summary=summary,
                metadata=metadata,
                content_hash=content_hash,
            )

        asset.org_id = org_id
        asset.type = type
        asset.source = source
        asset.title = title
        asset.content = content
        asset.summary = summary
        asset.asset_metadata = metadata or {}
        asset.content_hash = content_hash
        self.session.commit()
        self.session.refresh(asset)
        return asset

    def prune_project_sources(self, *, project_id: str, managed_source_uris: set[str]) -> int:
        statement = select(AssetModel).where(
            AssetModel.project_id == project_id,
            (
                (AssetModel.source == "git")
                | (AssetModel.source_uri == "agora://project-overview")
            ),
        )
        stale_assets = [
            asset
            for asset in self.session.scalars(statement).all()
            if asset.source_uri not in managed_source_uris
        ]
        for asset in stale_assets:
            self.session.delete(asset)
        self.session.commit()
        return len(stale_assets)
