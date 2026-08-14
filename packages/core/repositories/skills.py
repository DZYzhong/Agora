from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.core.models import SkillModel, SkillRunModel


class SkillRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        *,
        slug: str,
        name: str | None = None,
        status: str = "candidate",
        definition: dict | None = None,
        org_id: str | None = None,
        project_id: str | None = None,
    ) -> SkillModel:
        skill = SkillModel(
            org_id=org_id,
            project_id=project_id,
            slug=slug,
            name=name or slug,
            status=status,
            definition=definition or {},
        )
        self.session.add(skill)
        self.session.flush()
        self.session.refresh(skill)
        return skill

    def get(self, skill_id: str) -> SkillModel | None:
        return self.session.get(SkillModel, skill_id)

    def get_by_slug(self, skill_slug: str, *, project_id: str | None = None) -> SkillModel | None:
        statement = select(SkillModel).where(SkillModel.slug == skill_slug)
        if project_id is not None:
            statement = statement.where((SkillModel.project_id == project_id) | (SkillModel.project_id.is_(None)))
        return self.session.scalars(statement.order_by(SkillModel.project_id.desc().nullslast())).first()

    def list_by_project(self, project_id: str) -> list[SkillModel]:
        statement = select(SkillModel).where((SkillModel.project_id == project_id) | (SkillModel.project_id.is_(None)))
        return list(self.session.scalars(statement.order_by(SkillModel.slug.asc())).all())

    def update(
        self,
        skill_id: str,
        *,
        name: str | None = None,
        status: str | None = None,
        definition: dict | None = None,
    ) -> SkillModel:
        skill = self.get(skill_id)
        if skill is None:
            raise ValueError(f"Skill not found: {skill_id}")
        if name is not None:
            skill.name = name
        if status is not None:
            skill.status = status
        if definition is not None:
            skill.definition = definition
        self.session.flush()
        self.session.refresh(skill)
        return skill

    def create_run(
        self,
        *,
        org_id: str,
        project_id: str,
        skill_id: str,
        input: dict,
        output: dict,
        session_id: str | None = None,
        warnings: list[str] | None = None,
        status: str = "completed",
    ) -> SkillRunModel:
        run = SkillRunModel(
            org_id=org_id,
            project_id=project_id,
            session_id=session_id,
            skill_id=skill_id,
            input=input,
            output=output,
            warnings=warnings or [],
            status=status,
        )
        self.session.add(run)
        self.session.flush()
        self.session.refresh(run)
        return run

    def list_runs_by_project(self, project_id: str) -> list[SkillRunModel]:
        statement = select(SkillRunModel).where(SkillRunModel.project_id == project_id).order_by(SkillRunModel.created_at.desc())
        return list(self.session.scalars(statement).all())

    def list_runs_by_session(self, *, project_id: str, session_id: str) -> list[SkillRunModel]:
        statement = (
            select(SkillRunModel)
            .where(SkillRunModel.project_id == project_id, SkillRunModel.session_id == session_id)
            .order_by(SkillRunModel.created_at.asc())
        )
        return list(self.session.scalars(statement).all())
