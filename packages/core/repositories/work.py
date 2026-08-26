from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from packages.core.models import IdempotencyRecordModel, WorkItemLinkModel, WorkItemModel, WorkSessionModel, utc_now


@dataclass
class WorkSessionView:
    session: WorkSessionModel
    work_item: WorkItemModel

    @property
    def id(self) -> str:
        return self.session.id

    @property
    def org_id(self) -> str:
        return self.work_item.org_id

    @property
    def project_id(self) -> str:
        return self.work_item.project_id

    @property
    def task_id(self) -> str | None:
        return self.work_item.external_key

    @property
    def agent_type(self) -> str:
        return self.session.agent_type

    @property
    def intent(self) -> str:
        return self.session.intent

    @property
    def status(self) -> str:
        return self.session.status

    @status.setter
    def status(self, value: str) -> None:
        self.session.status = value

    @property
    def created_at(self) -> datetime:
        return self.session.created_at

    @property
    def closed_at(self) -> datetime | None:
        return self.session.closed_at

    @closed_at.setter
    def closed_at(self, value: datetime | None) -> None:
        self.session.closed_at = value

    @property
    def user_id(self) -> str:
        return self.session.user_id

    @property
    def credential_id(self) -> str | None:
        return self.session.credential_id

    @property
    def workflow_version_id(self) -> str | None:
        return self.session.workflow_version_id

    @property
    def workflow_execution_id(self) -> str | None:
        return self.session.workflow_execution_id

    @property
    def skill_version_id(self) -> str | None:
        return self.session.skill_version_id


class WorkRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_work_item(
        self,
        *,
        org_id: str,
        project_id: str,
        title: str,
        external_key: str | None = None,
        description: str | None = None,
        owner_id: str | None = None,
        source: str = "manual",
    ) -> WorkItemModel:
        work_item = WorkItemModel(
            org_id=org_id,
            project_id=project_id,
            title=title,
            external_key=external_key,
            description=description,
            owner_id=owner_id,
            source=source,
        )
        self.session.add(work_item)
        self.session.flush()
        self.session.refresh(work_item)
        return work_item

    def get_work_item(self, work_item_id: str) -> WorkItemModel | None:
        return self.session.get(WorkItemModel, work_item_id)

    def get_work_item_by_project(self, *, project_id: str, work_item_id: str) -> WorkItemModel | None:
        statement = select(WorkItemModel).where(WorkItemModel.project_id == project_id, WorkItemModel.id == work_item_id)
        return self.session.scalars(statement).first()

    def get_work_item_by_external_key(self, *, project_id: str, external_key: str) -> WorkItemModel | None:
        statement = select(WorkItemModel).where(
            WorkItemModel.project_id == project_id,
            WorkItemModel.external_key == external_key,
        )
        return self.session.scalars(statement).first()

    def find_work_items_by_title(self, *, project_id: str, title: str) -> list[WorkItemModel]:
        normalized = title.strip().casefold()
        if not normalized:
            return []
        statement = select(WorkItemModel).where(WorkItemModel.project_id == project_id)
        matches = []
        for item in self.session.scalars(statement).all():
            item_title = item.title.casefold()
            if normalized == item_title or normalized in item_title or item_title in normalized:
                matches.append(item)
        return matches

    def upsert_work_item_link(
        self,
        *,
        org_id: str,
        project_id: str,
        work_item_id: str,
        provider: str,
        external_key: str,
        external_url: str | None = None,
        title: str | None = None,
        status: str = "active",
        metadata: dict | None = None,
        created_by_user_id: str | None = None,
    ) -> WorkItemLinkModel:
        normalized_provider = provider.strip().lower()
        normalized_key = external_key.strip()
        statement = select(WorkItemLinkModel).where(
            WorkItemLinkModel.project_id == project_id,
            WorkItemLinkModel.provider == normalized_provider,
            WorkItemLinkModel.external_key == normalized_key,
        )
        link = self.session.scalars(statement).first()
        if link is None:
            link = WorkItemLinkModel(
                org_id=org_id,
                project_id=project_id,
                work_item_id=work_item_id,
                provider=normalized_provider,
                external_key=normalized_key,
                external_url=external_url,
                title=title,
                status=status,
                link_metadata=metadata or {},
                created_by_user_id=created_by_user_id,
            )
            self.session.add(link)
        else:
            link.work_item_id = work_item_id
            link.external_url = external_url or link.external_url
            link.title = title or link.title
            link.status = status or link.status
            link.link_metadata = {**(link.link_metadata or {}), **(metadata or {})}
        self.session.flush()
        self.session.refresh(link)
        return link

    def list_work_item_links_by_work_item_ids(self, work_item_ids: list[str]) -> list[WorkItemLinkModel]:
        if not work_item_ids:
            return []
        statement = (
            select(WorkItemLinkModel)
            .where(WorkItemLinkModel.work_item_id.in_(work_item_ids))
            .order_by(WorkItemLinkModel.provider.asc(), WorkItemLinkModel.external_key.asc())
        )
        return list(self.session.scalars(statement).all())

    def list_work_items_by_project(self, project_id: str) -> list[tuple[WorkItemModel, int]]:
        statement = (
            select(WorkItemModel, func.count(WorkSessionModel.id))
            .outerjoin(WorkSessionModel, WorkSessionModel.work_item_id == WorkItemModel.id)
            .where(WorkItemModel.project_id == project_id)
            .group_by(WorkItemModel.id)
            .order_by(WorkItemModel.updated_at.desc(), WorkItemModel.created_at.desc())
        )
        return [(work_item, session_count) for work_item, session_count in self.session.execute(statement).all()]

    def create_work_session(
        self,
        *,
        work_item_id: str,
        user_id: str,
        credential_id: str,
        agent_type: str,
        intent: str,
        initial_request_id: str | None = None,
        workflow_version_id: str | None = None,
        workflow_execution_id: str | None = None,
    ) -> WorkSessionView:
        work_session = WorkSessionModel(
            work_item_id=work_item_id,
            user_id=user_id,
            credential_id=credential_id,
            agent_type=agent_type,
            intent=intent,
            initial_request_id=initial_request_id,
            workflow_version_id=workflow_version_id,
            workflow_execution_id=workflow_execution_id,
        )
        self.session.add(work_session)
        self.session.flush()
        self.session.refresh(work_session)
        work_item = self.get_work_item(work_item_id)
        if work_item is None:
            raise ValueError(f"Work item not found: {work_item_id}")
        return WorkSessionView(session=work_session, work_item=work_item)

    def get_work_session(self, session_id: str) -> WorkSessionView | None:
        statement = (
            select(WorkSessionModel, WorkItemModel)
            .join(WorkItemModel, WorkItemModel.id == WorkSessionModel.work_item_id)
            .where(WorkSessionModel.id == session_id)
        )
        row = self.session.execute(statement).first()
        return WorkSessionView(session=row[0], work_item=row[1]) if row else None

    def get_work_session_by_project(self, *, project_id: str, session_id: str) -> WorkSessionView | None:
        statement = (
            select(WorkSessionModel, WorkItemModel)
            .join(WorkItemModel, WorkItemModel.id == WorkSessionModel.work_item_id)
            .where(WorkItemModel.project_id == project_id, WorkSessionModel.id == session_id)
        )
        row = self.session.execute(statement).first()
        return WorkSessionView(session=row[0], work_item=row[1]) if row else None

    def list_work_sessions_by_project(
        self,
        project_id: str,
        *,
        intent: str | None = None,
        status: str | None = None,
    ) -> list[WorkSessionView]:
        statement = (
            select(WorkSessionModel, WorkItemModel)
            .join(WorkItemModel, WorkItemModel.id == WorkSessionModel.work_item_id)
            .where(WorkItemModel.project_id == project_id)
            .order_by(WorkSessionModel.created_at.desc())
        )
        if intent:
            statement = statement.where(WorkSessionModel.intent == intent)
        if status:
            statement = statement.where(WorkSessionModel.status == status)
        return [
            WorkSessionView(session=work_session, work_item=work_item)
            for work_session, work_item in self.session.execute(statement).all()
        ]

    def list_work_sessions_by_work_item(self, work_item_id: str) -> list[WorkSessionView]:
        statement = (
            select(WorkSessionModel, WorkItemModel)
            .join(WorkItemModel, WorkItemModel.id == WorkSessionModel.work_item_id)
            .where(WorkSessionModel.work_item_id == work_item_id)
            .order_by(WorkSessionModel.created_at.desc())
        )
        return [
            WorkSessionView(session=work_session, work_item=work_item)
            for work_session, work_item in self.session.execute(statement).all()
        ]

    def create_idempotency_record(
        self,
        *,
        user_id: str,
        credential_id: str,
        operation: str,
        idempotency_key: str,
        request_hash: str,
        replay_window: timedelta,
    ) -> IdempotencyRecordModel:
        record = IdempotencyRecordModel(
            user_id=user_id,
            credential_id=credential_id,
            operation=operation,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            status="in_progress",
            replay_expires_at=utc_now() + replay_window,
        )
        self.session.add(record)
        self.session.flush()
        self.session.refresh(record)
        return record

    def get_idempotency_record(
        self,
        *,
        credential_id: str,
        operation: str,
        idempotency_key: str,
    ) -> IdempotencyRecordModel | None:
        statement = select(IdempotencyRecordModel).where(
            IdempotencyRecordModel.credential_id == credential_id,
            IdempotencyRecordModel.operation == operation,
            IdempotencyRecordModel.idempotency_key == idempotency_key,
        )
        return self.session.scalars(statement).first()

    def complete_idempotency_record(self, record: IdempotencyRecordModel, *, response_json: dict) -> IdempotencyRecordModel:
        record.response_json = response_json
        record.status = "completed"
        self.session.flush()
        self.session.refresh(record)
        return record
