from sqlalchemy.orm import Session

from packages.core.repositories.assets import AssetRepository
from packages.core.repositories.writebacks import WritebackRepository


class WritebackService:
    def __init__(self, session: Session):
        self.session = session
        self.writebacks = WritebackRepository(session)
        self.assets = AssetRepository(session)

    def list_by_project(self, project_id: str):
        return self.writebacks.list_by_project(project_id)

    def accept(self, writeback_id: str):
        writeback = self.writebacks.get(writeback_id)
        if writeback is None:
            raise ValueError(f"Writeback not found: {writeback_id}")
        asset = self.assets.create(
            org_id=writeback.org_id,
            project_id=writeback.project_id,
            type="writeback",
            source="agent",
            source_uri=f"writebacks/{writeback.id}",
            title=writeback.title,
            content=writeback.content,
            summary=writeback.content,
            metadata={"writeback_id": writeback.id, "writeback_type": writeback.type},
        )
        return self.writebacks.accept(writeback_id, accepted_asset_id=asset.id)

    def reject(self, writeback_id: str):
        writeback = self.writebacks.get(writeback_id)
        if writeback is None:
            raise ValueError(f"Writeback not found: {writeback_id}")
        writeback.status = "rejected"
        self.session.commit()
        self.session.refresh(writeback)
        return writeback
