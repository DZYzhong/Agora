from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.core.models import QualityEvidenceModel


class QualityRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_evidence(
        self,
        *,
        org_id: str,
        project_id: str,
        work_item_id: str,
        session_id: str | None,
        evidence_type: str,
        source: str,
        status: str,
        conclusion: str,
        command: str | None = None,
        output_summary: str | None = None,
        raw_ref: str | None = None,
        metadata: dict | None = None,
        created_by_user_id: str | None = None,
    ) -> QualityEvidenceModel:
        evidence = QualityEvidenceModel(
            org_id=org_id,
            project_id=project_id,
            work_item_id=work_item_id,
            session_id=session_id,
            evidence_type=evidence_type,
            source=source,
            status=status,
            conclusion=conclusion,
            command=command,
            output_summary=output_summary,
            raw_ref=raw_ref,
            evidence_metadata=metadata or {},
            created_by_user_id=created_by_user_id,
        )
        self.session.add(evidence)
        self.session.flush()
        self.session.refresh(evidence)
        return evidence

    def list_by_work_item(self, work_item_id: str) -> list[QualityEvidenceModel]:
        statement = (
            select(QualityEvidenceModel)
            .where(QualityEvidenceModel.work_item_id == work_item_id)
            .order_by(QualityEvidenceModel.created_at.desc(), QualityEvidenceModel.id)
        )
        return list(self.session.scalars(statement).all())

    def list_by_project(self, project_id: str) -> list[QualityEvidenceModel]:
        statement = (
            select(QualityEvidenceModel)
            .where(QualityEvidenceModel.project_id == project_id)
            .order_by(QualityEvidenceModel.created_at.desc(), QualityEvidenceModel.id)
        )
        return list(self.session.scalars(statement).all())
