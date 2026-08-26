from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.core.models import SkillModel, SkillRunModel, SkillVersionModel, WorkSessionModel


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

    def ensure_approved_version(self, skill_id: str, *, approved_by_user_id: str | None = None) -> SkillVersionModel:
        skill = self.get(skill_id)
        if skill is None:
            raise ValueError(f"Skill not found: {skill_id}")
        definition = {
            **(skill.definition or {}),
            "slug": skill.slug,
            "name": skill.name,
        }
        version = str(definition.get("version") or "1")
        existing = self.session.scalars(
            select(SkillVersionModel).where(
                SkillVersionModel.skill_id == skill.id,
                SkillVersionModel.version == version,
            )
        ).first()
        if existing is None:
            existing = SkillVersionModel(
                org_id=skill.org_id,
                project_id=skill.project_id,
                skill_id=skill.id,
                version=version,
                status="approved",
                definition=definition,
                approved_by_user_id=approved_by_user_id,
            )
            self.session.add(existing)
            self.session.flush()
            self.session.refresh(existing)
        skill.current_version_id = existing.id
        self.session.flush()
        self.session.refresh(skill)
        return existing

    def list_applicable_approved_versions(self, *, project_id: str, query: str, limit: int = 5) -> list[SkillVersionModel]:
        terms = {term.lower() for term in query.replace("，", " ").replace(",", " ").split() if term.strip()}
        statement = (
            select(SkillVersionModel, SkillModel)
            .join(SkillModel, SkillModel.id == SkillVersionModel.skill_id)
            .where(
                SkillVersionModel.status == "approved",
                SkillModel.status == "approved",
                SkillVersionModel.project_id == project_id,
            )
            .order_by(SkillModel.project_id.desc().nullslast(), SkillModel.slug.asc(), SkillVersionModel.created_at.desc())
        )
        scored: list[tuple[int, SkillVersionModel]] = []
        for version, skill in self.session.execute(statement).all():
            definition = version.definition or {}
            triggers = [str(trigger).lower() for trigger in definition.get("triggers") or []]
            slug_parts = skill.slug.lower().replace("-", " ").split()
            score = sum(1 for trigger in triggers if trigger and trigger in query.lower())
            if not triggers:
                score += sum(1 for part in slug_parts if part in terms)
            if score > 0:
                scored.append((score, version))
        scored.sort(key=lambda item: (-item[0], item[1].version))
        return [version for _, version in scored[:limit]]

    def get_version(self, skill_version_id: str) -> SkillVersionModel | None:
        return self.session.get(SkillVersionModel, skill_version_id)

    def get_current_version(self, skill_id: str) -> SkillVersionModel | None:
        skill = self.get(skill_id)
        if skill is None or skill.current_version_id is None:
            return None
        return self.get_version(skill.current_version_id)

    def create_run(
        self,
        *,
        org_id: str,
        project_id: str,
        skill_id: str,
        skill_version_id: str | None = None,
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
            skill_version_id=skill_version_id,
            input=input,
            output=output,
            warnings=warnings or [],
            status=status,
        )
        self.session.add(run)
        self.session.flush()
        self.session.refresh(run)
        return run

    def pin_work_session_skill_version(self, *, session_id: str, skill_version_id: str) -> None:
        work_session = self.session.get(WorkSessionModel, session_id)
        if work_session is None:
            return
        work_session.skill_version_id = skill_version_id
        self.session.flush()

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
