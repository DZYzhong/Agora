from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.core.models import WritebackModel


class WritebackRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        *,
        org_id: str,
        project_id: str,
        type: str,
        title: str,
        content: str,
        session_id: str | None = None,
        asset_refs: list[str] | None = None,
        status: str = "draft",
    ) -> WritebackModel:
        writeback = WritebackModel(
            org_id=org_id,
            project_id=project_id,
            session_id=session_id,
            type=type,
            title=title,
            content=content,
            asset_refs=asset_refs or [],
            status=status,
        )
        self.session.add(writeback)
        self.session.commit()
        self.session.refresh(writeback)
        return writeback

    def get(self, writeback_id: str) -> WritebackModel | None:
        return self.session.get(WritebackModel, writeback_id)

    def list_by_project(self, project_id: str) -> list[WritebackModel]:
        statement = select(WritebackModel).where(WritebackModel.project_id == project_id)
        return list(self.session.scalars(statement).all())

    def list_by_project_type_status(self, *, project_id: str, type: str, status: str) -> list[WritebackModel]:
        statement = select(WritebackModel).where(
            WritebackModel.project_id == project_id,
            WritebackModel.type == type,
            WritebackModel.status == status,
        )
        return list(self.session.scalars(statement).all())

    def list_by_ids(self, writeback_ids: list[str]) -> list[WritebackModel]:
        if not writeback_ids:
            return []
        statement = select(WritebackModel).where(WritebackModel.id.in_(writeback_ids))
        writebacks = list(self.session.scalars(statement).all())
        by_id = {writeback.id: writeback for writeback in writebacks}
        return [by_id[writeback_id] for writeback_id in writeback_ids if writeback_id in by_id]

    def accept(self, writeback_id: str, *, accepted_asset_id: str | None = None) -> WritebackModel:
        writeback = self.session.get(WritebackModel, writeback_id)
        if writeback is None:
            raise ValueError(f"Writeback not found: {writeback_id}")
        writeback.status = "accepted"
        writeback.accepted_asset_id = accepted_asset_id
        self.session.commit()
        self.session.refresh(writeback)
        return writeback
