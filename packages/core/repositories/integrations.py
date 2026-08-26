from __future__ import annotations

from sqlalchemy.orm import Session

from packages.core.models import RepositoryRevisionSignalModel


class IntegrationRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_repository_revision_signal(
        self,
        *,
        org_id: str,
        project_id: str,
        work_item_id: str | None,
        provider: str,
        repository_identity: str,
        branch: str,
        observed_head_sha: str,
        previous_head_sha: str | None = None,
        signal_type: str,
        status: str,
        raw_ref: str | None = None,
        metadata: dict | None = None,
        created_by_user_id: str | None = None,
    ) -> RepositoryRevisionSignalModel:
        signal = RepositoryRevisionSignalModel(
            org_id=org_id,
            project_id=project_id,
            work_item_id=work_item_id,
            provider=provider,
            repository_identity=repository_identity,
            branch=branch,
            observed_head_sha=observed_head_sha,
            previous_head_sha=previous_head_sha,
            signal_type=signal_type,
            status=status,
            raw_ref=raw_ref,
            signal_metadata=metadata or {},
            created_by_user_id=created_by_user_id,
        )
        self.session.add(signal)
        self.session.flush()
        self.session.refresh(signal)
        return signal
