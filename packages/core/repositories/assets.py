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
