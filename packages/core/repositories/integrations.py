from __future__ import annotations

from sqlalchemy.orm import Session

from packages.core.models import PullRequestSignalModel, RepositoryRevisionSignalModel


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

    def create_pull_request_signal(
        self,
        *,
        org_id: str,
        project_id: str,
        work_item_id: str | None,
        provider: str,
        repository_identity: str,
        pull_request_id: str,
        pull_request_url: str | None = None,
        title: str | None = None,
        action: str,
        source_branch: str | None = None,
        target_branch: str,
        head_sha: str | None = None,
        merge_commit_sha: str | None = None,
        status: str,
        metadata: dict | None = None,
        created_by_user_id: str | None = None,
    ) -> PullRequestSignalModel:
        signal = PullRequestSignalModel(
            org_id=org_id,
            project_id=project_id,
            work_item_id=work_item_id,
            provider=provider,
            repository_identity=repository_identity,
            pull_request_id=pull_request_id,
            pull_request_url=pull_request_url,
            title=title,
            action=action,
            source_branch=source_branch,
            target_branch=target_branch,
            head_sha=head_sha,
            merge_commit_sha=merge_commit_sha,
            status=status,
            signal_metadata=metadata or {},
            created_by_user_id=created_by_user_id,
        )
        self.session.add(signal)
        self.session.flush()
        self.session.refresh(signal)
        return signal
