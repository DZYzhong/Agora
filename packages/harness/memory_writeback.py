from packages.domain.schemas import AssetCreate


class MemoryWritebackService:
    def __init__(self, *, core, keyword_index, vector_index):
        self.core = core
        self.keyword_index = keyword_index
        self.vector_index = vector_index

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
        self.keyword_index.index_asset(asset.id, asset_payload)
        self.vector_index.index_asset(asset.id, asset_payload)
        return self.core.accept_writeback(writeback_id, accepted_asset_id=asset.id)

    def reject_writeback(self, writeback_id: str):
        writeback = self.core.get_writeback(writeback_id)
        if writeback is None:
            raise ValueError(f"Writeback not found: {writeback_id}")
        writeback.status = "rejected"
        return writeback
