from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.core.models import ContextPackModel


class ContextPackRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        *,
        id: str,
        org_id: str,
        project_id: str,
        level: str,
        summary: str,
        key_facts: list[dict],
        source_refs: list[dict],
    ) -> ContextPackModel:
        context_pack = ContextPackModel(
            id=id,
            org_id=org_id,
            project_id=project_id,
            level=level,
            summary=summary,
            key_facts=key_facts,
            source_refs=source_refs,
        )
        self.session.add(context_pack)
        self.session.flush()
        self.session.refresh(context_pack)
        return context_pack

    def list_by_project(self, project_id: str) -> list[ContextPackModel]:
        statement = (
            select(ContextPackModel)
            .where(ContextPackModel.project_id == project_id)
            .order_by(ContextPackModel.created_at.desc())
        )
        return list(self.session.scalars(statement).all())

    def list_by_ids(self, context_pack_ids: list[str]) -> list[ContextPackModel]:
        if not context_pack_ids:
            return []
        statement = select(ContextPackModel).where(ContextPackModel.id.in_(context_pack_ids))
        packs = list(self.session.scalars(statement).all())
        by_id = {pack.id: pack for pack in packs}
        return [by_id[pack_id] for pack_id in context_pack_ids if pack_id in by_id]
