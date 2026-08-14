from dataclasses import dataclass

from packages.domain.schemas import AssetCreate


@dataclass(frozen=True)
class PendingAssetIndex:
    asset_id: str
    asset: AssetCreate


@dataclass(frozen=True)
class AcceptWritebackResult:
    writeback: object
    pending_index: PendingAssetIndex


class MemoryWritebackService:
    def __init__(self, *, core):
        self.core = core

    def prepare_writeback(
        self,
        *,
        org_id: str,
        project_id: str,
        type: str,
        title: str,
        content: str,
        session_id: str | None = None,
        asset_refs: list[str] | None = None,
    ):
        return self.core.create_writeback(
            org_id=org_id,
            project_id=project_id,
            session_id=session_id,
            type=type,
            title=title,
            content=content,
            asset_refs=asset_refs or [],
            status="draft",
        )

    def accept_writeback(self, writeback_id: str):
        writeback = self.core.get_writeback(writeback_id)
        if writeback is None:
            raise ValueError(f"Writeback not found: {writeback_id}")

        asset_payload = AssetCreate(
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
        asset = self.core.create_asset(**asset_payload.model_dump())
        accepted = self.core.accept_writeback(writeback_id, accepted_asset_id=asset.id)
        self._create_candidate_skill_from_repeated_writebacks(accepted)
        return AcceptWritebackResult(
            writeback=accepted,
            pending_index=PendingAssetIndex(asset_id=asset.id, asset=asset_payload),
        )

    def reject_writeback(self, writeback_id: str):
        writeback = self.core.get_writeback(writeback_id)
        if writeback is None:
            raise ValueError(f"Writeback not found: {writeback_id}")
        writeback.status = "rejected"
        return writeback

    def _create_candidate_skill_from_repeated_writebacks(self, writeback) -> None:
        if not all(
            hasattr(self.core, method)
            for method in ("list_accepted_writebacks_by_type", "get_skill_by_slug", "create_skill")
        ):
            return
        accepted = self.core.list_accepted_writebacks_by_type(project_id=writeback.project_id, type=writeback.type)
        if len(accepted) < 2:
            return
        slug = writeback.type.replace("_", "-")
        existing = self.core.get_skill_by_slug(slug, project_id=writeback.project_id)
        if existing is not None:
            return
        self.core.create_skill(
            org_id=writeback.org_id,
            project_id=writeback.project_id,
            slug=slug,
            name=_title_from_slug(slug),
            status="candidate",
            definition={
                "version": "0.1.0",
                "source": "accepted_writebacks",
                "writeback_type": writeback.type,
                "triggers": [part for part in slug.split("-") if part],
                "input_schema": {"type": "object"},
                "instructions": accepted[-1].content,
                "evidence_writeback_ids": [item.id for item in accepted[-2:]],
            },
        )


def _title_from_slug(slug: str) -> str:
    return " ".join(part.capitalize() for part in slug.split("-") if part)
